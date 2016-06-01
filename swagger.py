import json
from flask.ext.restful import fields
from re import findall
from collections import defaultdict
from functools import reduce

_DEF_SWAGGER = {'swagger':'2.0',
                'consumes':'application/json',
                'produces':'application/json'}
_WANTED_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


class ReferenceField(fields.Raw):


    def __init__(self, ref_str):
        super().__init__()
        self._ref_str = ref_str


    def to_swagger(self):
        return {'$ref':'#/definitions/' + self._ref_str}


class Swagger(object):
    def __init__(self, **kwargs):
        self.models = defaultdict(list)
        self.header = dict(_DEF_SWAGGER)
        self.header.update(dict(kwargs))
        self.json = None


    def generate(self):
        if self.json:
            return self.json

        path_methods = defaultdict(list)
        for model in self.models.values():
            for path in model['paths']:
                path_methods[path] += [{'methods':_get_methods_for_path(path, model['cls']),
                                       'model_name':model['cls'].__name__}]

        schemas = {}
        path_methods = {path:_operations_to_sw(methods, schemas) for
                        path, methods in path_methods.items()}
        js = dict(self.header)
        js['paths'] = path_methods
        js['definitions'] = schemas
        self.json = js

        return self.json


    def dump_json(self, path):
        js = self.generate()
        with open(path, 'w') as f:
            json.dump(js, fp=f, indent=4, sort_keys=True)


    def operation(self, **kwargs):
        def decorate(func):
            sw_dict = dict(kwargs)
            if not 'description' in sw_dict:
                sw_dict.update({'description':func.__doc__})
            setattr(func, '__swagger', sw_dict)
            return func

        return decorate


    def model(self):
        def decorate(cls):
            self.models[cls] = {'cls':cls}
            return cls

        return decorate


    def register(self, model, paths):
        self.models[model]['paths'] = paths


JWT_HEADER = {'name':'Authorization', 'required':True, 'type':'string', 'in':'header'}


def path_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'path'}


def query_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'query'}


def _get_wanted_methods(model):
    return [getattr(model, method) for
            method in filter(lambda x: x in _WANTED_METHODS, dir(model))]


def _reference_schema(where:dict, schemas:dict):
    schema = where['schema']
    schema_name = list(schema.keys())[0]
    schema_payload = list(schema.values())[0]
    schemas[schema_name] = schema_payload
    where['schema'] = {'$ref':'#/definitions/' + schema_name}


def _expand_reference(where:dict, schemas:dict):
    ref = where.pop('reference')
    schema_name = 'generated-%s' % hash(ref['ref'])
    schemas[schema_name] = ref['ref']
    where['schema'] = {'$ref':'#/definitions/' + schema_name}


def _get_method_sw(method, model_name):
    sw_dict = method.__swagger
    sw_dict['tags'] = ['all']
    return sw_dict


def _operations_to_sw(operations:list, schemas:dict):
    # Extract methods from operations list.
    method_list = [op['methods'] for op in operations]
    method_list = reduce(lambda x, y: x + y, method_list)
    model_name = operations[0]['model_name']
    methods = {method.__name__:_get_method_sw(method, model_name)
               for method in method_list if hasattr(method, '__swagger')}

    for method in methods.values():
        # Set references for parameter schemas.

        for param in method['parameters']:
            if 'schema' in param:
                _reference_schema(param, schemas)
            if 'reference' in param:
                _expand_reference(param, schemas)

        # Set references for response schemes.
        for response in method['responses'].values():
            if 'schema' in response:
                _reference_schema(response, schemas)
            if 'reference' in response:
                _expand_reference(param, schemas)

    return methods


def _get_methods_for_path(path:str, model):
    path_variables = set(findall('<[^\:]*:([^>]*)', path))
    # Build a map: condensed method signature -> methods.
    methods = _get_wanted_methods(model)
    path_methods = []
    for m in methods:
        signature = set(param['name'] for param in
                        filter(lambda x: x['in'] == 'path', m.__swagger['parameters']))
        if signature == path_variables:
            path_methods.append(m)

    return path_methods


def _type_to_str(field_type):
    type_to_str = {fields.String:'string',
                   fields.Integer:'integer',
                   fields.Float:'float'}
    return type_to_str[type(field_type)]


def _field_to_string(field):
    if isinstance(field, fields.List):
        if isinstance(field.container, fields.Nested):
            items = {'type':'object'}
            sch = schema('generated', field.container.nested)
            items.update(sch['generated'])
            return {'type':'array', 'items':items}
        else:
            # Simple type.
            return {'type':'array', 'items':{'type':_type_to_str(field.container)}}
    elif isinstance(field, fields.Nested):
        sch = schema('generated', field.nested)
        items = {'type':'object'}
        items.update(sch['generated'])
        return {'type':items}

    return {'type':_type_to_str(field)}


def schema(name:str, json:dict):
    schema_vals = {k:_field_to_string(v) for k, v in json.items()}

    return {name:{"properties":schema_vals}}


def body_params(name:str, json:dict, req=True):
    return {'name':name, 'in':'body', 'schema':schema(name, json)}
