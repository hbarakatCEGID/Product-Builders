"""State Management Analyzer — Dimension 7 (HIGH IMPACT).

Detects state management library, data fetching library,
store structure, and state patterns.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, StateManagementResult

_STATE_LIBS: dict[str, str] = {
    "redux": "redux",
    "@reduxjs/toolkit": "redux-toolkit",
    "zustand": "zustand",
    "mobx": "mobx",
    "mobx-react": "mobx",
    "recoil": "recoil",
    "jotai": "jotai",
    "valtio": "valtio",
    "vuex": "vuex",
    "pinia": "pinia",
    "@ngrx/store": "ngrx",
    "effector": "effector",
    "xstate": "xstate",
    "@ngrx/signals": "ngrx-signals",
    "@legendapp/state": "legend-state",
    "nanostores": "nanostores",
    "@tanstack/store": "tanstack-store",
}

_DATA_FETCHING_LIBS: dict[str, str] = {
    "@tanstack/react-query": "tanstack-query",
    "react-query": "react-query",
    "swr": "swr",
    "@apollo/client": "apollo-client",
    "apollo-client": "apollo-client",
    "urql": "urql",
    "axios": "axios",
    "@tanstack/vue-query": "tanstack-query",
    "nuxt/apollo": "apollo-client",
    "rtk-query": "rtk-query",
    "@trpc/client": "trpc",
    "@trpc/server": "trpc",
    "react-relay": "relay",
    "relay-runtime": "relay",
    "ofetch": "ofetch",
    "ky": "ky",
}


class StateManagementAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "State Management Analyzer"

    @property
    def dimension(self) -> str:
        return "state_management"

    def analyze(self, repo_path: Path, *, index=None) -> StateManagementResult:
        state_lib = self._detect_state_lib(repo_path)
        data_fetching = self._detect_data_fetching(repo_path)
        store_structure = self._detect_store_structure(repo_path)
        patterns = self._detect_patterns(repo_path)

        # AST-enriched path: verify state library usage from actual imports
        if index is not None:
            state_libs = {
                "zustand": "zustand", "redux": "redux",
                "@reduxjs/toolkit": "redux", "mobx": "mobx",
                "recoil": "recoil", "jotai": "jotai", "valtio": "valtio",
                "pinia": "pinia", "vuex": "vuex",
            }
            for mod, lib_name in state_libs.items():
                if index.who_imports(mod):
                    state_lib = state_lib or lib_name
                    break

            data_fetch_libs = {
                "@tanstack/react-query": "react-query", "swr": "swr",
                "@apollo/client": "apollo", "urql": "urql",
            }
            for mod, lib_name in data_fetch_libs.items():
                if index.who_imports(mod):
                    data_fetching = data_fetching or lib_name
                    break

        return StateManagementResult(
            status=AnalysisStatus.SUCCESS,
            state_library=state_lib,
            data_fetching_library=data_fetching,
            store_structure=store_structure,
            state_patterns=patterns,
        )

    def _detect_state_lib(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if not pkg:
            return None
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for lib, name in _STATE_LIBS.items():
            if lib in deps:
                return name
        return None

    def _detect_data_fetching(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if not pkg:
            return None
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for lib, name in _DATA_FETCHING_LIBS.items():
            if lib in deps:
                return name
        return None

    def _detect_store_structure(self, repo_path: Path) -> str | None:
        store_dir = repo_path / "src" / "store"
        if not store_dir.is_dir():
            store_dir = repo_path / "src" / "stores"
        if not store_dir.is_dir():
            store_dir = repo_path / "store"
        if not store_dir.is_dir():
            return None

        subdirs = [d.name for d in store_dir.iterdir() if d.is_dir()]
        if subdirs:
            return f"modular ({', '.join(sorted(subdirs)[:5])})"

        files = [f.stem for f in store_dir.iterdir() if f.is_file() and f.suffix in (".ts", ".js", ".tsx", ".jsx")]
        if files:
            return f"flat ({', '.join(sorted(files)[:5])})"
        return None

    def _detect_patterns(self, repo_path: Path) -> list[str]:
        patterns: list[str] = []
        pkg = self.read_json(repo_path / "package.json")
        if not pkg:
            return patterns
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        if "@reduxjs/toolkit" in deps:
            patterns.append("Redux Toolkit slices")
        elif "redux" in deps:
            if "redux-saga" in deps:
                patterns.append("Redux + Sagas")
            elif "redux-thunk" in deps:
                patterns.append("Redux + Thunks")
            else:
                patterns.append("Redux")

        if "zustand" in deps:
            patterns.append("Zustand stores")
        if "mobx" in deps:
            patterns.append("MobX observables")
        if "pinia" in deps:
            patterns.append("Pinia stores")
        if "vuex" in deps:
            patterns.append("Vuex modules")

        if "react" in deps and not patterns:
            patterns.append("React Context / hooks")

        return patterns


register(StateManagementAnalyzer())
