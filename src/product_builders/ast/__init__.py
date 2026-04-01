"""Tree-sitter AST analysis — pre-pass for enriched heuristic analysis.

When tree-sitter loads successfully, the analyze pipeline builds a CodebaseIndex
before running analyzers. Each analyzer can query the index for imports, exports,
definitions, components, and naming patterns.

When tree-sitter is unavailable, analyzers work exactly as before.
"""

try:
    import tree_sitter as _ts  # noqa: F401

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Lazy imports to avoid importing tree-sitter transitively when it's absent
if TREE_SITTER_AVAILABLE:
    from product_builders.ast.builder import build_codebase_index
    from product_builders.ast.index import CodebaseIndex
else:
    from product_builders.ast.index import CodebaseIndex  # models are always importable

    def build_codebase_index(*_args: object, **_kwargs: object) -> None:  # type: ignore[misc]
        """No-op stub when tree-sitter is not installed."""
        return None

__all__ = [
    "TREE_SITTER_AVAILABLE",
    "CodebaseIndex",
    "build_codebase_index",
]
