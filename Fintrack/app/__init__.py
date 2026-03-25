from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

from config import DevelopmentConfig


# Create extensions at module level
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app(config_class=DevelopmentConfig):
    # 1. Create Flask app
    app = Flask(__name__)

    # 2. Load configuration
    app.config.from_object(config_class)

    # 3. Initialise SQLAlchemy
    db.init_app(app)

    # 4. Initialise Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "login"

    # 5. Initialise Flask-Bcrypt
    bcrypt.init_app(app)

    # 6. Return the configured app
    return app