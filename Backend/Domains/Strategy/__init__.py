"""
URL Shortening Strategies Package

Available strategies:
  - 'hashing'  : SHA-256 + custom charset (unique per call, uses timestamp)
  - 'base64'   : MD5 + base64 (deterministic — same URL always gives same code)
"""

from .Base64Strategy import Base64Strategy
from .HashingStrategy import HashingStrategy

__all__ = ['Base64Strategy', 'HashingStrategy', 'StrategyFactory']


class StrategyFactory:
    _strategies = {
        'base64': Base64Strategy,
        'hashing': HashingStrategy,
    }

    @staticmethod
    def get_strategy(name: str):
        if name not in StrategyFactory._strategies:
            available = list(StrategyFactory._strategies)
            raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
        return StrategyFactory._strategies[name]

    @staticmethod
    def get_available_strategies() -> list:
        return list(StrategyFactory._strategies)
