import os
from flask import Flask
from src.config import Config
from src.routes.portal_routes import portal_bp


def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.config.from_object(Config)
    app.register_blueprint(portal_bp)
    return app
