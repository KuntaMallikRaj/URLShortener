from datetime import datetime
from extensions import db


class URLModel(db.Model):
    __tablename__ = 'urls'

    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.Text, nullable=False)
    short_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    click_count = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'original_url': self.original_url,
            'short_code': self.short_code,
            'created_at': self.created_at.isoformat(),
            'click_count': self.click_count,
        }

    def __repr__(self):
        return f'<URL {self.short_code}>'
