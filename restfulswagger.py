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

from flask_restful import fields
from re import findall
from re import sub
from collections import defaultdict
from functools import reduce

# Implicit parameters.
_DEF_SWAGGER = {'swagger':'2.0',
                'consumes':['application/json'],
                'produces':['application/json']}


def _get_wanted_methods(model):
    # Get relevant methods from class definition.
    WANTED_METHODS = {'get', 'post', 'put', 'patch', 'delete'}
    return [getattr(model, method) for
            method in filter(lambda x: x in WANTED_METHODS, dir(model))]


def _reference_schema(where:dict, schemas:dict):
    # Add schema from 'where' into global schemas.
    schema = where['schema']
    schema_name = list(schema.keys())[0]
    schema_payload = list(schema.values())[0]
    schemas[schema_name] = schema_payload
    # Schema added, replace with reference.
    where['schema'] = {'$ref':'#/definitions/' + schema_name}


def _get_method_sw(method, model_name):
    # Add tags to method documentation, the 'all' tag is implicit.
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
        # Get path parameter names
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


'''
Swagger 2.0 for Flask-RESTful Resource classes.
'''
class Swagger(object):


    '''
        Create Swagger documentation object. Expected parameters:
         - info={'version':API_VERSION, 'description':API DESCRIPTION}
         - host : hostname of the server, format: hostname:port
         - schemes : a list with supported schemes (http, https)
    '''
    def __init__(self, **kwargs):
        self.models = defaultdict(list)
        self.header = dict(_DEF_SWAGGER)
        self.header.update(dict(kwargs))
        self.json = None


    '''
        Returns a dictionary according to Swagger 2.0 spec.
    '''
    def generate(self):
        if self.json:
            return self.json

        path_methods = defaultdict(list)
        for model in self.models.values():
            for path in model['paths']:
                path_methods[path] += [{'methods':_get_methods_for_path(path, model['cls']),
                                       'model_name':model['cls'].__name__}]

        schemas = {}
        # We need to replace <type:id> with {id} so that Swagger UI works.
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
         - parameters: a list with method parameters (use {path, query, body, header}_param
         - responses: a dict with response codes and descriptions
    '''
    def operation(self, **kwargs):
        def decorate(func):
            sw_dict = dict(kwargs)
            if not 'description' in sw_dict:
                # Use docstring as description if missing.
                sw_dict.update({'description':func.__doc__})
            # Save Swagger operation as class method attribute.
            setattr(func, '__swagger', sw_dict)
            return func

        return decorate


    '''
        Use this as a decorator for Flask RESTFul Response classes.
    '''
    def model(self):
        def decorate(cls):
            self.models[cls] = {'cls':cls}
            return cls

        return decorate


    '''
        Use this function to register Flask path with Flask RESTful resource.
    '''
    def register(self, model, paths):
        self.models[model]['paths'] = paths


'''Use this to add named references to response and body objects to documentation.'''
def schema(name:str, schema_fields:dict):
    # Replace flask_restful.fields with strings.
    schema_vals = {k:_field_to_string(v) for k, v in schema_fields.items()}
    return {name:{"properties":schema_vals}}


'''Use this to add path parameter to documentation. Integer is the default type.'''
def path_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'path'}


'''Use this to add query parameter to documentation. Integer is the default type.'''
def query_param(name:str, param_type='integer'):
    return {'name':name, 'required':True, 'type':param_type, 'in':'query'}


'''Use this to add body parameter to documentation. Expect a dict with flask_restful.fields values.'''
def body_params(name:str, body_fields:dict):
    return {'name':name, 'in':'body', 'schema':schema(name, body_fields)}


'''Use this to add query parameter to documentation.'''
def header_params(name:str, param_type):
    return {'name':name, 'required':True, 'in':'header', 'type':param_type}
