from datetime import datetime

class URLdetails:
    """Class to represent URL details without database"""
    
    def __init__(self, original_url, short_code, user_id=None):
        self.id = None
        self.original_url = original_url
        self.short_code = short_code
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.click_count = 0

    def __repr__(self):
        return f'<URL {self.short_code}: {self.original_url[:50]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'original_url': self.original_url,
            'short_code': self.short_code,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'click_count': self.click_count
        }

    def increment_clicks(self):
        self.click_count += 1
    