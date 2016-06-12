# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
from flask_restful import fields
from re import findall
from re import sub
from collections import defaultdict
from functools import reduce

_DEF_SWAGGER = {'swagger':'2.0',
                'consumes':['application/json'],
                'produces':['application/json']}


'''
Swagger 2.0 for Flask-RESTful Resource classes.
'''
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
        replace_ids = lambda path: sub('<.*?:(.*?)>', r'{\1}', path)
        path_methods = {replace_ids(path):_operations_to_sw(methods, schemas) for
                        path, methods in path_methods.items()}
        js = dict(self.header)
        js['paths'] = path_methods
        js['definitions'] = schemas
        self.json = js

        return self.json


    '''
        Use this as a decorator for GET, POST, PUT, PATCH and DELETE methods.
        expected arguments:
         - description: a string with method description
         - parameters: a list with method parameters (use path_param, query_param, body_param or header_param
         - responses: a dict with response codes and descriptions.
    '''
    def operation(self, **kwargs):
        def decorate(func):
            sw_dict = dict(kwargs)
            if not 'description' in sw_dict:
                # Use docstring as description if missing
                sw_dict.update({'description':func.__doc__})
            # Save Swagger operation as class method attribute
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


def _get_wanted_methods(model):
    WANTED_METHODS = {'get', 'post', 'put', 'patch', 'delete'}
    return [getattr(model, method) for
            method in filter(lambda x: x in WANTED_METHODS, dir(model))]


def _reference_schema(where:dict, schemas:dict):
    schema = where['schema']
    schema_name = list(schema.keys())[0]
    schema_payload = list(schema.values())[0]
    schemas[schema_name] = schema_payload
    where['schema'] = {'$ref':'#/definitions/' + schema_name}


def _get_method_sw(method, model_name):
    sw_dict = method.__swagger
    sw_dict['tags'] = ['all', model_name]
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

        # Set references for response schemes.
        for response in method['responses'].values():
            if 'schema' in response:
                _reference_schema(response, schemas)

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
                   fields.Float:'float',
                   fields.Boolean:'bool'}
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
        return items

    return {'type':_type_to_str(field)}


def schema(name:str, json:dict):
    schema_vals = {k:_field_to_string(v) for k, v in json.items()}
    return {name:{"properties":schema_vals}}


def path_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'path'}


def query_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'query'}


def body_params(name:str, json:dict):
    return {'name':name, 'in':'body', 'schema':schema(name, json)}


def header_params(name:str, param_type, req=True):
    return {'name':name, 'required':req, 'in':'header', 'type':param_type}
