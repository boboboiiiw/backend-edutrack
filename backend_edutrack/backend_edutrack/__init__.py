from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from backend_edutrack.utils.auth_policy import get_role_from_email
from .models.meta import DBSession  
from pyramid.renderers import JSON
from .models import Base            

def cors_tween_factory(handler, registry):
    def cors_tween(request):
        # Allow specific origin (not *)
        allowed_origin = 'http://localhost:5173'

        if request.method == 'OPTIONS':
            # Preflight response
            response = request.response
            response.headers['Access-Control-Allow-Origin'] = allowed_origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Max-Age'] = '3600'
            
            return response

        # Actual response
        response = handler(request)
        response.headers['Access-Control-Allow-Origin'] = allowed_origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response

    return cors_tween

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application. """
    engine = engine_from_config(settings, "sqlalchemy.")

    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include('pyramid_jinja2')
    config.include('.routes')
    config.include('.models')
    config.include('pyramid_tm')
    config.include('pyramid_retry')

    # Tambahkan middleware autentikasi
    config.add_renderer('json', JSON(indent=4))
    config.add_tween('backend_edutrack.utils.auth_policy.auth_tween_factory')
    config.add_tween('.cors_tween_factory')

    config.scan()
    return config.make_wsgi_app()