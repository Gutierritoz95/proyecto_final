import os
from flask import Flask
from .database import init_app as init_database


def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        static_folder=os.path.join(project_root, 'static'),
        template_folder=project_root,
    )
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tecnoburger-dev-secret')
    init_database(app)
    from .routes import register_routes
    register_routes(app)
    return app