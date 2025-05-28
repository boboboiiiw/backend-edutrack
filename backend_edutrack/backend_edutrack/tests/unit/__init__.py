# In backend_edutrack/__init__.py

from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
# Import 'register' instead of 'ZopeTransactionExtension'
from zope.sqlalchemy import register 
from pyramid.config import Configurator
import transaction # You already have this for your tests, but good to ensure it's here

# ... (other imports like Base from .models.meta)

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings) as config:
        # 1. Setup SQLAlchemy engine
        engine = engine_from_config(settings, 'sqlalchemy.')

        # 2. Create the DBSession factory
        # DO NOT pass 'extension=ZopeTransactionExtension()' here anymore
        DBSession = sessionmaker(bind=engine)
        

        # 3. Register the DBSession factory with zope.sqlalchemy
        # This is the new way to integrate the transaction manager
        register(DBSession)

        # 4. IMPORTANT: Register the DBSession factory in the application's registry
        config.registry['dbsession'] = DBSession
        config.registry['db_engine'] = engine # Good practice to also store the engine

        # 5. Include your application's other configurations (routes, views, pyramid_tm)
        config.include('pyramid_tm') # Make sure this is included
        config.include('.routes') 
        config.scan('.') # Scan for views and other configured components

    return config.make_wsgi_app()