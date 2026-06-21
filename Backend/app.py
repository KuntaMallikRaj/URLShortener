import os
import sys

# Ensure Backend directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, limiter


def _init_bloom_filter():
    """
    Populate the Redis Bloom filter with all short codes already in the DB.
    Skipped if the filter key already exists (e.g. app restart without Redis flush).
    Called once inside the app context at startup.
    """
    import logging

    from extensions import redis_client
    from Models.URLModel import URLModel
    from Utils.BloomFilter import BloomFilter

    try:
        if redis_client.exists(BloomFilter.KEY):
            return  # Filter is already populated; keep existing bits

        existing_codes = [
            row.short_code
            for row in URLModel.query.with_entities(URLModel.short_code).all()
        ]
        if existing_codes:
            BloomFilter.initialize(redis_client, existing_codes)
    except Exception:  # noqa: BLE001 - never let a Redis hiccup crash startup
        # Redis may be briefly unreachable during a deploy. The Bloom filter is
        # an optimization, not a correctness requirement (collisions still fall
        # back to a DB lookup), so log and continue booting.
        logging.getLogger(__name__).warning(
            "Could not initialize Bloom filter from Redis; continuing without it",
            exc_info=True,
        )


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)
    limiter.init_app(app)

    # Wire up a read replica session if READ_REPLICA_URL is configured and
    # differs from the primary. Falls back to db.session (primary) otherwise.
    replica_url = app.config.get('READ_REPLICA_URL')
    primary_url = app.config['SQLALCHEMY_DATABASE_URI']
    if replica_url and replica_url != primary_url:
        import extensions
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, scoped_session

        replica_engine = create_engine(replica_url)
        ReplicaSession = scoped_session(sessionmaker(bind=replica_engine))
        extensions._replica_scoped_session = ReplicaSession

        @app.teardown_appcontext
        def _remove_replica_session(exc=None):
            ReplicaSession.remove()

    # Import models before create_all() so their tables are registered on
    # db.metadata. Without this import, metadata is empty and create_all()
    # silently creates no tables — breaking the first write on a fresh database.
    from Models.URLModel import URLModel  # noqa: F401

    with app.app_context():
        db.create_all()
        _init_bloom_filter()

    from Controllers.URLController import URLController

    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Frontend')

    @app.route('/')
    def index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/healthz')
    @limiter.exempt
    def healthz():
        """Lightweight health check for Render. Verifies DB connectivity;
        reports Redis status without failing the check (Redis is optional)."""
        from sqlalchemy import text

        from extensions import redis_client

        status = {'status': 'ok', 'database': 'ok', 'redis': 'ok'}
        try:
            db.session.execute(text('SELECT 1'))
        except Exception:
            status['status'] = 'error'
            status['database'] = 'error'
        try:
            redis_client.ping()
        except Exception:
            status['redis'] = 'unavailable'

        return jsonify(status), (200 if status['status'] == 'ok' else 503)

    @app.route('/api/shorten', methods=['POST'])
    @limiter.limit("10 per minute")
    def shorten():
        return URLController.shorten()

    @app.route('/api/stats/<short_code>', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_stats(short_code):
        return URLController.get_stats(short_code)

    @app.route('/api/recent', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_recent():
        return URLController.get_recent()

    # This must come last so it doesn't swallow /api/* routes
    @app.route('/<short_code>')
    @limiter.limit("60 per minute")
    def redirect_url(short_code):
        return URLController.redirect_url(short_code)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
