import hashlib


class BloomFilter:
    """
    Redis-backed Bloom filter for O(1) short code collision detection.

    Uses double hashing (Kirsch-Mitzenmacher method) to derive K bit
    indices from two base hashes, avoiding K separate hash computations.

    Sizing for 1 million short codes at ~1% false-positive rate:
      m (bits)  = 9,585,059  (~1.2 MB stored in a single Redis BITSET)
      k (hashes) = 7
    """

    KEY = "bloom:short_codes"
    M = 9_585_059  # bit array size
    K = 7          # number of hash functions

    @staticmethod
    def _bit_indices(value: str) -> list[int]:
        """
        Derive K bit positions for value using double hashing:
            index_i = (h1 + i * h2) mod M
        """
        h1 = int(hashlib.md5(value.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha256(value.encode()).hexdigest(), 16)
        return [(h1 + i * h2) % BloomFilter.M for i in range(BloomFilter.K)]

    @classmethod
    def add(cls, redis_client, value: str) -> None:
        """Register a short code in the filter."""
        pipe = redis_client.pipeline()
        for idx in cls._bit_indices(value):
            pipe.setbit(cls.KEY, idx, 1)
        pipe.execute()

    @classmethod
    def might_exist(cls, redis_client, value: str) -> bool:
        """
        Return True if the short code *might* already exist (check DB to confirm).
        Return False if it definitely does not exist (skip DB entirely).
        """
        pipe = redis_client.pipeline()
        for idx in cls._bit_indices(value):
            pipe.getbit(cls.KEY, idx)
        return all(pipe.execute())

    @classmethod
    def initialize(cls, redis_client, short_codes) -> None:
        """
        Bulk-load existing short codes on startup.
        Called once when Redis has no filter yet (e.g. after a Redis restart).
        Uses a non-transactional pipeline for speed.
        """
        pipe = redis_client.pipeline(transaction=False)
        for code in short_codes:
            for idx in cls._bit_indices(code):
                pipe.setbit(cls.KEY, idx, 1)
        pipe.execute()
