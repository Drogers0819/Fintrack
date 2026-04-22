import os


class DevelopmentConfig:
    SECRET_KEY = "dev-secret-key"
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable static file caching in dev


class TestingConfig:
    SECRET_KEY = "test-secret-key"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")  # Set in Render/Railway env vars