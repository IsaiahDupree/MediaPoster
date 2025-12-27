"""
Media Factory Data Contracts
============================
Stable interfaces (schemas) for all data structures in the pipeline.

These contracts enable:
- Provider swapping
- Multi-server rendering
- Version compatibility
- Schema validation
"""

from .trend_card import TrendCardSchema
from .cluster import ClusterSchema
from .content_brief import ContentBriefSchema
from .script import ScriptSchema
from .timeline import TimelineSchema
from .render_job import RenderJobSchema
from .publish_job import PublishJobSchema

__all__ = [
    "TrendCardSchema",
    "ClusterSchema",
    "ContentBriefSchema",
    "ScriptSchema",
    "TimelineSchema",
    "RenderJobSchema",
    "PublishJobSchema",
]

