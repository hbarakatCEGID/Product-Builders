"""Testing Analyzer — Dimension 13 (MEDIUM IMPACT).

Detects test framework, runner, directories, file patterns,
mocking library, coverage tools, and e2e frameworks.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, TestingResult

_TEST_FRAMEWORK_FILES: dict[str, str] = {
    "jest.config.js": "jest",
    "jest.config.ts": "jest",
    "jest.config.cjs": "jest",
    "jest.config.mjs": "jest",
    "vitest.config.ts": "vitest",
    "vitest.config.js": "vitest",
    "vitest.config.mts": "vitest",
    "karma.conf.js": "karma",
    "pytest.ini": "pytest",
    "conftest.py": "pytest",
    "phpunit.xml": "phpunit",
    "phpunit.xml.dist": "phpunit",
    ".rspec": "rspec",
    "spec_helper.rb": "rspec",
}

_MOCKING_LIBS: dict[str, str] = {
    "jest-mock": "jest",
    "sinon": "sinon",
    "nock": "nock",
    "msw": "msw",
    "unittest.mock": "unittest.mock",
    "pytest-mock": "pytest-mock",
    "mockito": "mockito",
    "moq": "moq",
    "factory_boy": "factory-boy",
    "faker": "faker",
    "responses": "responses",
    "requests-mock": "requests-mock",
    "vcrpy": "vcrpy",
    "@faker-js/faker": "faker",
    "mockall": "mockall",
}

_COVERAGE_TOOLS: dict[str, str] = {
    "nyc": "nyc",
    "istanbul": "istanbul",
    "c8": "c8",
    "coverage": "coverage.py",
    "pytest-cov": "pytest-cov",
    "jacoco": "jacoco",
    "simplecov": "simplecov",
    "cargo-tarpaulin": "tarpaulin",
    "coverlet.collector": "coverlet",
}

_E2E_FRAMEWORKS: dict[str, str] = {
    "cypress": "cypress",
    "playwright": "playwright",
    "@playwright/test": "playwright",
    "selenium": "selenium",
    "puppeteer": "puppeteer",
    "nightwatch": "nightwatch",
    "testcafe": "testcafe",
    "webdriverio": "webdriverio",
    "@wdio/cli": "webdriverio",
    "detox": "detox",
}


class TestingAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Testing Analyzer"

    @property
    def dimension(self) -> str:
        return "testing"

    def analyze(self, repo_path: Path, *, index=None) -> TestingResult:
        framework, runner = self._detect_framework(repo_path)
        test_dirs = self._detect_test_dirs(repo_path)
        file_pattern = self._detect_file_pattern(repo_path)
        mocking = self._detect_mocking(repo_path)
        coverage_tool, coverage_config = self._detect_coverage(repo_path)
        e2e = self._detect_e2e(repo_path)
        fixtures = self._detect_fixtures(repo_path)

        if not framework:
            pyproject = repo_path / "pyproject.toml"
            if pyproject.exists():
                content = self.read_file(pyproject)
                if content:
                    if "pytest" in content or "[tool.pytest" in content:
                        framework = "pytest"
                    elif "unittest" in content:
                        framework = "unittest"

        if not framework:
            pkg = self.read_json(repo_path / "package.json")
            if pkg:
                scripts = pkg.get("scripts", {})
                test_script = scripts.get("test", "")
                if "vitest" in test_script:
                    framework = "vitest"
                elif "jest" in test_script:
                    framework = "jest"
                elif "mocha" in test_script:
                    framework = "mocha"

        return TestingResult(
            status=AnalysisStatus.SUCCESS,
            test_framework=framework,
            test_runner=runner,
            test_directories=test_dirs,
            test_file_pattern=file_pattern,
            mocking_library=mocking,
            coverage_tool=coverage_tool,
            coverage_config_path=coverage_config,
            fixture_patterns=fixtures,
            e2e_framework=e2e,
        )

    def _detect_framework(self, repo_path: Path) -> tuple[str | None, str | None]:
        for filename, fw in _TEST_FRAMEWORK_FILES.items():
            if (repo_path / filename).exists():
                return fw, fw
        return None, None

    def _detect_test_dirs(self, repo_path: Path) -> list[str]:
        candidates = ["tests", "test", "spec", "specs", "__tests__", "src/__tests__", "src/test"]
        return [d for d in candidates if (repo_path / d).is_dir()]

    def _detect_file_pattern(self, repo_path: Path) -> str | None:
        test_dirs = self._detect_test_dirs(repo_path)
        scan_dirs = [repo_path / d for d in test_dirs] if test_dirs else [repo_path]

        patterns = {"*.test.*": 0, "*.spec.*": 0, "test_*.py": 0, "*_test.py": 0, "*Test.java": 0}
        for scan_dir in scan_dirs:
            if not scan_dir.is_dir():
                continue
            for f in list(scan_dir.rglob("*"))[:200]:
                if not f.is_file():
                    continue
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                stem = f.stem
                name = f.name
                if ".test." in name:
                    patterns["*.test.*"] += 1
                elif ".spec." in name:
                    patterns["*.spec.*"] += 1
                elif stem.startswith("test_"):
                    patterns["test_*.py"] += 1
                elif stem.endswith("_test"):
                    patterns["*_test.py"] += 1
                elif stem.endswith("Test"):
                    patterns["*Test.java"] += 1

        best = max(patterns, key=lambda k: patterns[k])
        return best if patterns[best] > 0 else None

    def _detect_mocking(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        for lib, name in _MOCKING_LIBS.items():
            if lib in deps:
                return name
        return None

    def _detect_coverage(self, repo_path: Path) -> tuple[str | None, str | None]:
        deps = self.collect_dependency_names(repo_path)
        for lib, name in _COVERAGE_TOOLS.items():
            if lib in deps:
                return name, None
        if (repo_path / ".nycrc").exists() or (repo_path / ".nycrc.json").exists():
            return "nyc", ".nycrc"
        if (repo_path / ".coveragerc").exists():
            return "coverage.py", ".coveragerc"
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = self.read_file(pyproject)
            if content and "[tool.coverage" in content:
                return "coverage.py", "pyproject.toml"
        return None, None

    def _detect_e2e(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        for lib, name in _E2E_FRAMEWORKS.items():
            if lib in deps:
                return name
        if (repo_path / "cypress.config.js").exists() or (repo_path / "cypress.config.ts").exists():
            return "cypress"
        if (repo_path / "playwright.config.ts").exists() or (repo_path / "playwright.config.js").exists():
            return "playwright"
        return None

    def _detect_fixtures(self, repo_path: Path) -> list[str]:
        fixture_dirs = ["fixtures", "test/fixtures", "tests/fixtures", "__fixtures__", "tests/data"]
        return [d for d in fixture_dirs if (repo_path / d).is_dir()]


register(TestingAnalyzer())
