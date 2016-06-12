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

from datetime import datetime
from random import choice

from flask_restful import Resource
from flask_restful import fields

from todolist_swagger import swagger

from restfulswagger import path_param
from restfulswagger import schema
from restfulswagger import body_params


def _random_task(id):
    return {'id':id,
            'priority':0,
            'date_due':datetime.now().isoformat(),
            'description':''.join(choice('abcdefgh') for _ in range(32)),
            'completed':False}


'''Resource representing single task, POST and GET methods.'''
@swagger.model()
class TaskResource(Resource):


    '''Input body fields.'''
    __json_in = {
        'priority'      :  fields.Integer(),
        'date_due'      :  fields.String(),
        'description'   :  fields.String()
    }

    '''Output body fields.'''
    json_out = {
        'id'            :  fields.Integer(),
        'priority'      :  fields.Integer(),
        'date_due'      :  fields.String(),
        'description'   :  fields.String(),
        'completed'     :  fields.Boolean()
    }


    '''
        Use the "operation" decorator to create swagger for the method.
        This is a simple POST with body parameters only. We have to specify
        the parameters using the "body_param" function, it expects a dict with flask_restful fields.
        Upon creation, this endpoint returns 201 + id. We can put this into docs using the "schema" function.
        First parameter of the "schema" function is and ID of schema (we need this because of the way Swagger JSON is structured).
        ID must be unique. Second parameter is again a dict with field names and field types.
    '''
    @swagger.operation(
        description='Create a new task',
        parameters=[body_params('task_body', __json_in)],
        responses={204:{'description':'Task created', 'schema':schema('create_task', {'id':fields.Integer()})}})
    def post(self):
        return {'id':1337}, 201


    '''
        Simple GET method returning single task.
        This endpoint expects one path parameter, use "path_param" for that, integer is the default second parameter.
        Again, use schema to specify what gets returned by the endpoint.
    '''
    @swagger.operation(
        description='Get task by ID',
        parameters=[path_param('id')],
        responses={200:{'description':'OK', 'schema':schema('task', json_out)}})
    def get(self, id):
        return _random_task(id), 200


'''Resource representing multiple tasks.'''
@swagger.model()
class TasksResource(Resource):

    #Notice use of the "Nested" field, we need both for singlular references and for list with references.
    __json_out = {
       'tasks'  :  fields.List(fields.Nested(TaskResource.json_out)),
       'user'   :  fields.Nested({'id':fields.Integer(), 'name':fields.String()})
    }


    '''
        Although this method returns multiple tasks in a list, the parameters are the same as for the single one.
        Be careful to specify the fields properly, if referencing other object, you must use fields.Nested.
    '''
    @swagger.operation(
        description='Get all tasks',
        parameters=[],
        responses={200:{'description':'OK', 'schema':schema('tasks', __json_out)}})
    def get(self):
        return {'tasks':[_random_task(id) for id in range(4)], 'user':{'id':1, 'name':'Roy Batty'}}, 200


'''This resource returns generated Swagger JSON.'''
class DocsResource(Resource):
    def get(self):
        return swagger.generate(), 200
