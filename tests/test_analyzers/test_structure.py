from __future__ import annotations

"""Tests for StructureAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.structure import StructureAnalyzer


def test_detects_source_directory(tmp_path: Path) -> None:
    """Creating src/ should detect it as a source directory."""
    (tmp_path / "src").mkdir()

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "src" in result.source_directories


def test_detects_key_directories(tmp_path: Path) -> None:
    """Directories like src/components and src/pages should appear in key_directories."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "components").mkdir()
    (src / "pages").mkdir()

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    key_paths = [kd.path for kd in result.key_directories]
    assert any("components" in p for p in key_paths)
    assert any("pages" in p for p in key_paths)


def test_detects_feature_based_organization(tmp_path: Path) -> None:
    """Creating src/features/ and src/modules/ should detect feature-based organization.

    The detector requires ALL markers in the pattern list to match. For
    'feature-based' those are 'features/' and 'modules/'.
    """
    src = tmp_path / "src"
    (src / "features").mkdir(parents=True)
    (src / "modules").mkdir()

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.module_organization == "feature-based"


def test_detects_layered_organization(tmp_path: Path) -> None:
    """Creating src/controllers, src/services, src/models should detect layered organization."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "controllers").mkdir()
    (src / "services").mkdir()
    (src / "models").mkdir()
    (src / "repositories").mkdir()

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.module_organization == "layered"


def test_detects_monorepo_with_lerna(tmp_path: Path) -> None:
    """packages/ dir + lerna.json should detect monorepo with lerna tool."""
    (tmp_path / "packages").mkdir()
    (tmp_path / "lerna.json").write_text(json.dumps({"version": "0.0.0"}))

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.is_monorepo is True
    assert result.monorepo_tool == "lerna"


def test_detects_monorepo_with_turborepo(tmp_path: Path) -> None:
    """apps/ dir + turbo.json should detect monorepo with turborepo tool."""
    (tmp_path / "apps").mkdir()
    (tmp_path / "turbo.json").write_text(json.dumps({"pipeline": {}}))

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.is_monorepo is True
    assert result.monorepo_tool == "turborepo"


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo should have empty root_directories."""
    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.root_directories == []
    assert result.status.value == "success"


def test_anti_pattern_no_source_directory(tmp_path: Path) -> None:
    """No src/lib/app dirs should trigger the 'no standard source directory' anti-pattern."""
    # Create a directory that is NOT a standard source dir
    (tmp_path / "stuff").mkdir()

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no standard source directory" in ap for ap in result.anti_patterns)


def test_detects_sub_projects(tmp_path: Path) -> None:
    """Monorepo with packages containing package.json should populate sub_projects."""
    packages = tmp_path / "packages"
    packages.mkdir()

    pkg_a = packages / "web"
    pkg_a.mkdir()
    (pkg_a / "package.json").write_text(json.dumps({"name": "@app/web"}))

    pkg_b = packages / "api"
    pkg_b.mkdir()
    (pkg_b / "package.json").write_text(json.dumps({"name": "@app/api"}))

    # Need a monorepo marker or >1 sub_projects for is_monorepo
    (tmp_path / "lerna.json").write_text(json.dumps({"version": "0.0.0"}))

    analyzer = StructureAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.is_monorepo is True
    assert len(result.sub_projects) == 2
    sub_names = [sp.replace("\\", "/") for sp in result.sub_projects]
    assert "packages/web" in sub_names
    assert "packages/api" in sub_names
