from ..models import UserAccount, UserRole
from .decorators import login_required, role_required

from .decorators import login_required
from flask import Blueprint, request, session

from ..database import db
from ..models import UserAccount
from ..security import verify_password

auth_bp = Blueprint("auth", __name__)

def find_user_by_email(email: str):
    return db.session.execute(
        db.select(UserAccount).where(
            UserAccount.email == email
        )
    ).scalar_one_or_none()

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {
            "error": "Email and password are required"
        }, 400

    user = find_user_by_email(email)

    if user is None or not verify_password(
        user.password_hash,
        password,
    ):
        return {
            "error": "Invalid credentials"
        }, 401

    session["user_id"] = user.user_id

    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.user_role.value,
        }
    }, 200



@auth_bp.post("/logout")
def logout():
    session.clear()

    return {
        "message": "Logged out successfully"
    }, 200


@auth_bp.get("/me")
@login_required
def current_user():
    user_id = session["user_id"]
    user = db.session.get(UserAccount, user_id)

    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.user_role.value,
        }
    }, 200

