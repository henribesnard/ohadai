"""
Document parser module for extracting OHADA hierarchy from Word documents
"""

from .parser import OhadaDocumentParser
from .extractor import HierarchyExtractor

__all__ = ["OhadaDocumentParser", "HierarchyExtractor"]
