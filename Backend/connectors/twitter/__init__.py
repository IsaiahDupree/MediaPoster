"""
Twitter/X Platform Connector

This connector handles Twitter/X integration for:
- Publishing tweets and threads
- Fetching tweet metrics and analytics
- DM functionality (via Safari automation fallback)

Uses Blotato API for publishing and Twitter API v2 for metrics.
"""

from .connector import TwitterConnector

__all__ = ["TwitterConnector"]
