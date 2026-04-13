from sqlalchemy.exc import SQLAlchemyError

from extensions import db, get_read_session
from Models.URLModel import URLModel


class URLRepository:

    @staticmethod
    def _read(query_fn):
        """
        Execute query_fn against the read replica.
        If the replica is unavailable (OperationalError, timeout, etc.)
        and a replica is actually configured, retry transparently against
        the primary so requests never fail due to replica downtime.
        """
        session = get_read_session()
        try:
            return query_fn(session)
        except SQLAlchemyError:
            if session is not db.session:
                # Replica failed — fall back to primary
                return query_fn(db.session)
            raise  # No replica configured; this is a real primary error

    # ------------------------------------------------------------------ reads

    @staticmethod
    def find_by_short_code(short_code: str):
        return URLRepository._read(
            lambda s: s.query(URLModel).filter_by(short_code=short_code).first()
        )

    @staticmethod
    def find_by_original_url(original_url: str):
        return URLRepository._read(
            lambda s: s.query(URLModel).filter_by(original_url=original_url).first()
        )

    @staticmethod
    def get_all() -> list:
        return URLRepository._read(
            lambda s: s.query(URLModel).order_by(URLModel.created_at.desc()).limit(10).all()
        )

    # ----------------------------------------------------------------- writes
    # INSERT / UPDATE always go to the primary via db.session.

    @staticmethod
    def save(original_url: str, short_code: str) -> URLModel:
        url = URLModel(original_url=original_url, short_code=short_code)
        db.session.add(url)
        db.session.commit()
        return url

    @staticmethod
    def increment_clicks_by_code(short_code: str) -> None:
        db.session.query(URLModel).filter_by(short_code=short_code).update(
            {'click_count': URLModel.click_count + 1}
        )
        db.session.commit()
