"""Phase 2: Cursor-assisted deep analysis via bootstrap meta-rules and structured prompts.

Workflow:
  1. ``analyze`` generates an adaptive bootstrap .mdc rule using heuristic context
  2. User opens repo in Cursor and says "run deep analysis"
  3. Cursor follows 3 steps (architecture, domain model, conventions),
     writing findings to ``deep-analysis.yaml``
  4. ``ingest-deep`` validates evidence citations and merges into the profile
  5. ``generate`` produces richer rules informed by the deep data
"""

from product_builders.deep_analysis.ingest import (
    DEEP_SECTIONS,
    ingest_deep_analysis,
    load_deep_yaml,
    strip_evidence,
)
from product_builders.deep_analysis.prompts import (
    build_adaptive_questions,
    build_gap_aware_questions,
    get_output_yaml_example,
)
from product_builders.deep_analysis.schema import (
    DeepAnalysisYAML,
    is_evidence_key,
    validate_deep_yaml,
)

__all__ = [
    "DEEP_SECTIONS",
    "DeepAnalysisYAML",
    "build_adaptive_questions",
    "build_gap_aware_questions",
    "get_output_yaml_example",
    "ingest_deep_analysis",
    "is_evidence_key",
    "load_deep_yaml",
    "strip_evidence",
    "validate_deep_yaml",
]
