from functools import wraps

from flask import session

from ..database import db
from ..models import UserAccount


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")

        if user_id is None:
            return {
                "error": "Authentication required"
            }, 401

        user = db.session.get(UserAccount, user_id)

        if user is None:
            session.clear()

            return {
                "error": "Authentication required"
            }, 401

        return view_function(*args, **kwargs)

    return wrapped_view


def role_required(required_role):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            user_id = session.get("user_id")

            if user_id is None:
                return {
                    "error": "Authentication required"
                }, 401

            user = db.session.get(UserAccount, user_id)

            if user is None:
                session.clear()

                return {
                    "error": "Authentication required"
                }, 401

            if user.user_role != required_role:
                return {
                    "error": "Forbidden"
                }, 403

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator