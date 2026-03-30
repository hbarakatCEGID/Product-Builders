from __future__ import annotations

"""Tests for DependencyAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.dependencies import DependencyAnalyzer


def test_detects_npm_dependencies(tmp_path: Path) -> None:
    """package.json with deps and devDeps should detect correct counts."""
    pkg = {
        "dependencies": {
            "react": "^18.2.0",
            "next": "14.0.0",
        },
        "devDependencies": {
            "typescript": "^5.0.0",
        },
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert len(result.dependencies) == 3
    prod_deps = [d for d in result.dependencies if not d.is_dev]
    dev_deps = [d for d in result.dependencies if d.is_dev]
    assert len(prod_deps) == 2
    assert len(dev_deps) == 1
    assert "package.json" in result.dependency_manifest_files


def test_detects_python_requirements(tmp_path: Path) -> None:
    """requirements.txt with packages should detect deps."""
    (tmp_path / "requirements.txt").write_text(
        "flask>=2.0.0\nrequests==2.28.0\n# comment\npydantic\n"
    )

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    dep_names = [d.name for d in result.dependencies]
    assert "flask" in dep_names
    assert "requests" in dep_names
    assert "pydantic" in dep_names


def test_detects_lock_file_npm(tmp_path: Path) -> None:
    """package-lock.json should set lock_file."""
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}))
    (tmp_path / "package-lock.json").write_text("{}")

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.lock_file == "package-lock.json"


def test_detects_lock_file_yarn(tmp_path: Path) -> None:
    """yarn.lock should set lock_file."""
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {}}))
    (tmp_path / "yarn.lock").write_text("# yarn lockfile v1")

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.lock_file == "yarn.lock"


def test_categorizes_known_packages(tmp_path: Path) -> None:
    """Known packages like react, jest, eslint should have correct categories."""
    pkg = {
        "dependencies": {"react": "^18.0.0"},
        "devDependencies": {"jest": "^29.0.0", "eslint": "^8.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    by_name = {d.name: d for d in result.dependencies}
    assert by_name["react"].category == "ui-framework"
    assert by_name["jest"].category == "testing"
    assert by_name["eslint"].category == "linting"


def test_detects_pyproject_toml_deps(tmp_path: Path) -> None:
    """pyproject.toml with [project.dependencies] should detect deps."""
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"myapp\"\n\n"
        "[project.dependencies]\n"
        "fastapi>=0.100.0\n"
        "pydantic>=2.0\n"
    )

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    dep_names = [d.name for d in result.dependencies]
    assert "fastapi" in dep_names
    assert "pyproject.toml" in result.dependency_manifest_files


def test_detects_go_mod_deps(tmp_path: Path) -> None:
    """go.mod with a require block should detect deps."""
    (tmp_path / "go.mod").write_text(
        "module example.com/mymod\n\n"
        "go 1.21\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.1\n"
        "\tgithub.com/lib/pq v1.10.9\n"
        ")\n"
    )

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    dep_names = [d.name for d in result.dependencies]
    assert "github.com/gin-gonic/gin" in dep_names
    assert "github.com/lib/pq" in dep_names
    assert "go.mod" in result.dependency_manifest_files


def test_detects_cargo_toml_deps(tmp_path: Path) -> None:
    """Cargo.toml with [dependencies] should detect deps."""
    (tmp_path / "Cargo.toml").write_text(
        "[package]\nname = \"myapp\"\nversion = \"0.1.0\"\n\n"
        "[dependencies]\n"
        "serde = \"1.0\"\n"
        "tokio = { version = \"1\", features = [\"full\"] }\n\n"
        "[dev-dependencies]\n"
        "criterion = \"0.5\"\n"
    )

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    dep_names = [d.name for d in result.dependencies]
    assert "serde" in dep_names
    assert "tokio" in dep_names
    assert "criterion" in dep_names
    # criterion should be dev
    criterion_dep = [d for d in result.dependencies if d.name == "criterion"]
    assert criterion_dep[0].is_dev is True
    assert "Cargo.toml" in result.dependency_manifest_files


def test_empty_repo_no_deps(tmp_path: Path) -> None:
    """Empty repo should have no dependencies."""
    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.dependencies == []
    assert result.status.value == "success"


def test_anti_pattern_no_lock_file(tmp_path: Path) -> None:
    """package.json but no lock file should trigger anti-pattern."""
    pkg = {"dependencies": {"express": "^4.18.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no lock file" in ap for ap in result.anti_patterns)


def test_anti_pattern_no_manifest(tmp_path: Path) -> None:
    """No dependency manifest at all should trigger anti-pattern."""
    analyzer = DependencyAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no dependency manifest" in ap for ap in result.anti_patterns)
