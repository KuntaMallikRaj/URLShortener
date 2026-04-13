import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Support both sqlite (dev) and postgres (production)
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///urls.db')

    # Render provides postgres:// but SQLAlchemy 1.4+ requires postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEFAULT_STRATEGY = os.environ.get('DEFAULT_STRATEGY', 'hashing')

    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    RATELIMIT_STORAGE_URI = REDIS_URL

    # Optional: point at a PostgreSQL read replica for SELECT queries.
    # Falls back to the primary when not set.
    READ_REPLICA_URL = os.environ.get('READ_REPLICA_URL')
