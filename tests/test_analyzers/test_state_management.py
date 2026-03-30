from __future__ import annotations

"""Tests for state management analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.state_management import StateManagementAnalyzer


def test_detects_redux(tmp_path: Path) -> None:
    """package.json with @reduxjs/toolkit should detect redux-toolkit."""
    pkg = {"dependencies": {"@reduxjs/toolkit": "^2.0.0", "react": "^18.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.state_library == "redux-toolkit"


def test_detects_zustand(tmp_path: Path) -> None:
    """package.json with zustand should detect zustand."""
    pkg = {"dependencies": {"zustand": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.state_library == "zustand"


def test_detects_tanstack_query(tmp_path: Path) -> None:
    """package.json with @tanstack/react-query should detect tanstack-query."""
    pkg = {"dependencies": {"@tanstack/react-query": "^5.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.data_fetching_library == "tanstack-query"


def test_detects_modular_store(tmp_path: Path) -> None:
    """store/ dir with subdirectories should detect modular store structure."""
    store = tmp_path / "store"
    store.mkdir()
    (store / "auth").mkdir()
    (store / "cart").mkdir()
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.store_structure is not None
    assert "modular" in result.store_structure


def test_detects_react_hook_form(tmp_path: Path) -> None:
    """package.json with react-hook-form should detect form library."""
    pkg = {"dependencies": {"react-hook-form": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.form_library == "react-hook-form"


def test_detects_socket_io_realtime(tmp_path: Path) -> None:
    """package.json with socket.io-client should detect realtime library."""
    pkg = {"dependencies": {"socket.io-client": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.realtime_library == "socket.io"


def test_detects_multiple_state_libs(tmp_path: Path) -> None:
    """package.json with redux and zustand should detect both in state_libraries."""
    pkg = {"dependencies": {"redux": "^5.0.0", "zustand": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "redux" in result.state_libraries
    assert "zustand" in result.state_libraries


def test_empty_repo_no_state(tmp_path: Path) -> None:
    """Empty repo should have no state library detected."""
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.state_library is None


def test_anti_pattern_multiple_state_libs(tmp_path: Path) -> None:
    """3+ state management libraries should trigger anti-pattern."""
    pkg = {
        "dependencies": {
            "redux": "^5.0.0",
            "zustand": "^4.0.0",
            "mobx": "^6.0.0",
        }
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = StateManagementAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("multiple state" in ap.lower() for ap in result.anti_patterns)
