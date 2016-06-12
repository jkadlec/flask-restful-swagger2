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

from flask.ext.restful import Resource
from flask.ext.restful import fields

from todolist_swagger import swagger

from restfulswagger import JWT_HEADER
from restfulswagger import path_param
from restfulswagger import schema
from restfulswagger import body_params

from flask.ext.restful import reqparse
from flask.ext.restful import fields


@swagger.model()
class TaskResource(Resource):

    '''Generic task to be '''

    __json_in = {
        'priority'      :  fields.Integer(),
        'date_due'      :  fields.String(),
        'description'   :  fields.String()
    }

    __json_out = {
        'priority': fields.Integer(),
        'date_due': fields.String(),
        'description'   :  fields.String(),
        'completed'   :  fields.Boolean()
    }


    @swagger.operation(
        description='Create a new task',
        parameters=[body_params('task_body', __json_in)],
        responses={204:{'description':'Task created'}})
    def post(self):
        return {}, 201


    @swagger.operation(
        description='Get task by ID',
        parameters=[path_param('id')],
        responses={200:{'description':'OK', 'schema':schema('single_task', __json_out)}})
    def get(self, id):
        return {'foo':'bar'}, 200


class DocsResource(Resource):
    def get(self):
        return swagger.generate(), 200

