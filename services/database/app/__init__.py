from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .database import db
from .http import register_error_handlers

migrate = Migrate()

API_PREFIX = "/api"


def register_cors(app):
    """Allow the browser app to call this API with its session cookie.

    ``supports_credentials`` is what makes the browser send and store the
    session cookie on cross-origin calls; it also obliges us to name the
    permitted origins, since browsers reject a wildcard on a credentialed
    request.
    """
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
    )


def register_transaction_boundary(app):
    """Commit a request's work, or discard it.

    Services stop at ``db.session.flush()``: they make their writes
    visible to later queries in the same request without deciding that
    the request as a whole succeeded.  That decision belongs to the
    request, so it is made once here rather than in every route.

    A response of 400 or worse means a domain rule refused the request,
    so whatever was written before that point is rolled back and the
    request leaves no trace.
    """

    @app.after_request
    def commit_or_rollback(response):
        if response.status_code >= 400:
            db.session.rollback()

            return response

        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise

        return response

    @app.teardown_request
    def discard_on_failure(exception=None):
        # An exception that escaped the view means ``after_request`` never
        # ran, or ran before the failure surfaced; either way the work
        # must not survive.
        if exception is not None:
            db.session.rollback()


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)

    from . import models
    from .routes.auth import auth_bp
    from .routes.coordinator import coordinator_bp
    from .routes.office import office_bp
    from .routes.reference import reference_bp
    from .routes.student import student_bp

    # Everything the browser app calls lives under /api, which keeps the
    # API namespace clear of the single-page app's own routes: the SPA
    # also navigates to /student/... and /office/..., so an unprefixed API
    # would collide with it behind a dev proxy or a single domain.
    for blueprint in (auth_bp, reference_bp, student_bp, coordinator_bp, office_bp):
        app.register_blueprint(
            blueprint,
            url_prefix=f"{API_PREFIX}{blueprint.url_prefix or ''}",
        )

    register_cors(app)
    register_error_handlers(app)
    register_transaction_boundary(app)

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
