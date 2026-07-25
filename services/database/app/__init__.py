from flask import Flask
from .database import db

def create_app():
    app = Flask(__name__)

    return app
