"""
SUBSENSE — Feature Extractor (Compatibility Re-export)
Re-exports FeatureExtractor and FeatureVector from app.processing.features.
"""

from app.processing.features import FeatureExtractor
from app.processing.schemas import FeatureVector

__all__ = ["FeatureExtractor", "FeatureVector"]
