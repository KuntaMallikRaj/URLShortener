import os

import redis as redis_lib
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)
redis_client = redis_lib.from_url(
    os.environ.get('REDIS_URL', 'redis://localhost:6379'),
    decode_responses=True,
)

# Populated by create_app() when READ_REPLICA_URL is configured.
# None means no replica is set — reads fall back to the primary db.session.
_replica_scoped_session = None


def get_read_session():
    """
    Return the read-replica session if one is configured, otherwise fall back
    to the primary Flask-SQLAlchemy session.

    All SELECT queries in URLRepository go through this function so that
    routing is transparent: swapping in a replica requires only setting
    READ_REPLICA_URL in the environment.
    """
    if _replica_scoped_session is not None:
        return _replica_scoped_session
    return db.session
