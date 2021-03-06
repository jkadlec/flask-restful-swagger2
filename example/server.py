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

from flask import Flask
from flask import request
from flask_restful import Api as RESTfulAPI
from flask_cors import CORS

from resources import TaskResource
from resources import TasksResource
from resources import DocsResource

from todolist_swagger import swagger

_API_VERSION = 0.1

app = Flask('TODO-list-swagger')
CORS(app)

rest_api = RESTfulAPI(app, catch_all_404s=True)


def _add_resource(api, res, paths):
    swagger.register(res, paths)
    api.add_resource(res, *paths)


def _register_routes(rest_api):
    # Endpoints.
    _add_resource(rest_api, TaskResource, ['/api/v%s/task/<int:id>' % _API_VERSION, '/api/v%s/task' % _API_VERSION])
    _add_resource(rest_api, TasksResource, ['/api/v%s/tasks' % _API_VERSION])
    # Swagger Docs.
    rest_api.add_resource(DocsResource, '/api/v%s/spec' % _API_VERSION)


def _init_app():
    _register_routes(rest_api)


with app.app_context():
    _init_app()
    if __name__ == '__main__':
        app.run()
