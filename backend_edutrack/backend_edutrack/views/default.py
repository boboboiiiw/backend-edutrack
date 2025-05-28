from pyramid.response import Response
from pyramid.view import view_config

@view_config(route_name='home')
def hello_world_view(request):
    return Response('Hello, World!')
