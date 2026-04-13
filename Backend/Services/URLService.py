import json

from Repositories.URLRepository import URLRepository
from Domains.Strategy.HashingStrategy import HashingStrategy
from Domains.Strategy.Base64Strategy import Base64Strategy


class URLData:
    """Lightweight container for Redis-cached URL data."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        return dict(self.__dict__)


class URLService:

    @staticmethod
    def shorten_url(original_url: str, strategy: str = 'hashing'):
        from extensions import redis_client
        from Utils.BloomFilter import BloomFilter

        # Return existing record if this URL was already shortened
        existing = URLRepository.find_by_original_url(original_url)
        if existing:
            # Warm the redirect cache in case it's missing
            redis_client.setex(f"url:redirect:{existing.short_code}", 3600, existing.original_url)
            return existing

        encoder = Base64Strategy if strategy == 'base64' else HashingStrategy

        # Generate a unique short code, using the Bloom filter to avoid
        # unnecessary DB queries. might_exist() == False means the code is
        # definitely free; True means it *might* collide (confirm with DB).
        short_code = encoder.encode_url(original_url)
        attempts = 0
        while attempts < 10:
            if BloomFilter.might_exist(redis_client, short_code):
                # Possible collision — confirm with a DB query
                if URLRepository.find_by_short_code(short_code):
                    # Real collision: regenerate and retry
                    short_code = encoder.encode_url(original_url + short_code)
                    attempts += 1
                    continue
                # Bloom false positive — code is actually free, use it
            break  # Bloom says definitely free, or false positive resolved

        url = URLRepository.save(original_url, short_code)
        # Register the new code in the Bloom filter and warm the redirect cache
        BloomFilter.add(redis_client, url.short_code)
        redis_client.setex(f"url:redirect:{url.short_code}", 3600, url.original_url)
        return url

    @staticmethod
    def get_original_url(short_code: str):
        """Fetch URL and increment its click counter. Uses Redis cache for the redirect lookup."""
        from extensions import redis_client

        cache_key = f"url:redirect:{short_code}"
        cached_url = redis_client.get(cache_key)

        if cached_url:
            # Cache hit: skip the SELECT, fire a direct UPDATE for click count
            URLRepository.increment_clicks_by_code(short_code)
            return URLData(original_url=cached_url)

        # Cache miss: query replica, populate cache, increment on primary
        url = URLRepository.find_by_short_code(short_code)
        if url:
            redis_client.setex(cache_key, 3600, url.original_url)
            URLRepository.increment_clicks_by_code(short_code)
        return url

    @staticmethod
    def get_stats(short_code: str):
        return URLRepository.find_by_short_code(short_code)

    @staticmethod
    def get_recent_urls():
        """Return 10 most recent URLs. Cached in Redis for 30 seconds."""
        from extensions import redis_client

        cache_key = "url:recent"
        cached = redis_client.get(cache_key)
        if cached:
            return [URLData(**item) for item in json.loads(cached)]

        urls = URLRepository.get_all()
        redis_client.setex(cache_key, 30, json.dumps([u.to_dict() for u in urls]))
        return urls
