from restfulswagger import Swagger

swagger = Swagger(info={'version':'0.1', 'description':'TODO list REST API'},
                  host='localhost:5000', basePath='', schemes=['http'])
