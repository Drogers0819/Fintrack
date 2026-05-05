import os


def _normalize_db_url(url):
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _normalize_db_url(os.environ.get("DATABASE_URL"))


class DevelopmentConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///dev.db"
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Disable static file caching in dev
    POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY")
    POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    EMAIL_FROM = os.environ.get("EMAIL_FROM")
    EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME")
    CRON_SECRET = os.environ.get("CRON_SECRET")


class TestingConfig:
    SECRET_KEY = "test-secret-key"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    POSTHOG_API_KEY = None
    POSTHOG_HOST = None
    RESEND_API_KEY = None
    EMAIL_FROM = None
    EMAIL_FROM_NAME = None
    CRON_SECRET = None


class ProductionConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///dev.db"
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    EMAIL_FROM = os.environ.get("EMAIL_FROM")
    EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME")
    POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY")
    POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")
    CRON_SECRET = os.environ.get("CRON_SECRET")
