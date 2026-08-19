from flask import Flask
from flask_migrate import Migrate
from .database import db
from .config import Config

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    from . import models

    @app.get("/health/database")
    def database_health():
        try:
            result = db.session.execute(
                text("SELECT 1")
            ).scalar_one()

            return {
                "status": "ok",
                "database_result": result,
            }

        except SQLAlchemyError:
            return {
                "status": "error",
                "message": "Database connection failed",
            }, 503
    return app
