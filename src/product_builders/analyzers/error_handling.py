"""Error Handling & Logging Analyzer — Dimension 5 (HIGH IMPACT).

Detects error handling strategy, logging framework, monitoring integration,
error response format, and custom error classes.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import SKIP_DIRS, BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, ErrorHandlingResult

LOGGING_FRAMEWORK_INDICATORS: dict[str, list[str]] = {
    "winston": ["winston"],
    "pino": ["pino"],
    "bunyan": ["bunyan"],
    "log4js": ["log4js"],
    "morgan": ["morgan"],
    "loglevel": ["loglevel"],
    "python-logging": ["logging"],
    "loguru": ["loguru"],
    "structlog": ["structlog"],
    "log4j": ["log4j", "org.apache.logging.log4j"],
    "slf4j": ["slf4j", "org.slf4j"],
    "logback": ["logback", "ch.qos.logback"],
    "serilog": ["Serilog"],
    "nlog": ["NLog"],
    "rails-logger": ["Rails.logger"],
}

MONITORING_INDICATORS: dict[str, list[str]] = {
    "sentry": ["@sentry/node", "@sentry/react", "@sentry/browser", "sentry-sdk", "sentry_sdk", "Sentry"],
    "datadog": ["dd-trace", "datadog", "ddtrace"],
    "new-relic": ["newrelic", "new_relic_rpm"],
    "bugsnag": ["@bugsnag/js", "bugsnag"],
    "rollbar": ["rollbar"],
    "honeybadger": ["honeybadger", "@honeybadger-io/js"],
    "application-insights": ["applicationinsights", "Microsoft.ApplicationInsights"],
}


class ErrorHandlingAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Error Handling & Logging Analyzer"

    @property
    def dimension(self) -> str:
        return "error_handling"

    def analyze(self, repo_path: Path) -> ErrorHandlingResult:
        dep_names = self._collect_dep_names(repo_path)
        logging_fw = self._detect_logging_framework(dep_names, repo_path)
        logging_config = self._detect_logging_config(repo_path)
        monitoring = self._detect_monitoring(dep_names)
        error_strategy = self._detect_error_strategy(repo_path)
        error_format = self._detect_error_response_format(repo_path)
        custom_errors = self._detect_custom_error_classes(repo_path)

        return ErrorHandlingResult(
            status=AnalysisStatus.SUCCESS,
            error_strategy=error_strategy,
            logging_framework=logging_fw,
            logging_config_file=logging_config,
            monitoring_integration=monitoring,
            error_response_format=error_format,
            custom_error_classes=custom_errors,
        )

    def _collect_dep_names(self, repo_path: Path) -> set[str]:
        deps: set[str] = set()
        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            data = self.read_json(pkg_json)
            if data:
                for section in ["dependencies", "devDependencies"]:
                    deps.update(data.get(section, {}).keys())

        for req_file in self.find_files(repo_path, "requirements*.txt"):
            content = self.read_file(req_file)
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith(("#", "-")):
                        name = re.split(r"[><=!~\[]", line)[0].strip()
                        if name:
                            deps.add(name)

        for csproj in self.find_files(repo_path, "*.csproj"):
            content = self.read_file(csproj)
            if content:
                for m in re.finditer(r'Include="([^"]+)"', content):
                    deps.add(m.group(1))

        return deps

    def _detect_logging_framework(self, dep_names: set[str], repo_path: Path) -> str | None:
        for fw, indicators in LOGGING_FRAMEWORK_INDICATORS.items():
            if fw == "python-logging":
                continue
            if any(ind in dep_names for ind in indicators):
                return fw

        # Check for Python stdlib logging usage
        for py_file in self.find_files(repo_path, "src/**/*.py"):
            content = self.read_file(py_file)
            if content and "import logging" in content:
                return "python-logging"
            break

        return None

    def _detect_logging_config(self, repo_path: Path) -> str | None:
        config_files = [
            "logging.conf", "logging.ini", "logging.yaml", "logging.yml",
            "log4j.properties", "log4j2.xml", "logback.xml", "logback-spring.xml",
            "nlog.config", "serilog.json",
        ]
        for cf in config_files:
            if (repo_path / cf).exists():
                return cf

        # Check for logging in config directories
        for pattern in ["config/logging*", "conf/logging*"]:
            matches = self.find_files(repo_path, pattern)
            if matches:
                return str(matches[0].relative_to(repo_path))

        return None

    def _detect_monitoring(self, dep_names: set[str]) -> str | None:
        for monitor, indicators in MONITORING_INDICATORS.items():
            if any(ind in dep_names for ind in indicators):
                return monitor
        return None

    def _detect_error_strategy(self, repo_path: Path) -> str | None:
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path
        count = 0

        exception_count = 0
        result_type_count = 0

        for path in scan_dir.rglob("*"):
            if count >= 30:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".rs", ".go"):
                continue

            content = self.read_file(path)
            if not content:
                continue
            count += 1

            exception_count += content.count("throw ") + content.count("raise ") + content.count("throws ")
            result_type_count += content.count("Result<") + content.count("Either<") + content.count("Result.Ok")

        if result_type_count > exception_count and result_type_count > 0:
            return "result-types"
        if exception_count > 0:
            return "exceptions"
        return None

    def _detect_error_response_format(self, repo_path: Path) -> str | None:
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path
        count = 0

        for path in scan_dir.rglob("*"):
            if count >= 15:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in (".ts", ".js", ".py", ".java", ".cs"):
                continue

            content = self.read_file(path)
            if not content:
                continue
            count += 1

            # Look for error response structures
            if re.search(r'(error|message|statusCode|status_code).*json', content, re.IGNORECASE):
                return "json"
            if re.search(r'\.json\(\s*\{.*error', content, re.IGNORECASE):
                return "json"

        return None

    def _detect_custom_error_classes(self, repo_path: Path) -> list[str]:
        custom_errors: list[str] = []
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path
        count = 0

        for path in scan_dir.rglob("*"):
            if count >= 30:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs"):
                continue

            content = self.read_file(path)
            if not content:
                continue
            count += 1

            # TypeScript/JavaScript: class XxxError extends Error
            for m in re.finditer(r"class\s+(\w+Error)\s+extends\s+(?:Error|BaseError|HttpException)", content):
                if m.group(1) not in custom_errors:
                    custom_errors.append(m.group(1))

            # Python: class XxxError(Exception) or class XxxError(BaseException)
            for m in re.finditer(r"class\s+(\w+(?:Error|Exception))\s*\(", content):
                if m.group(1) not in custom_errors:
                    custom_errors.append(m.group(1))

            # Java: class XxxException extends RuntimeException
            for m in re.finditer(r"class\s+(\w+Exception)\s+extends\s+\w+Exception", content):
                if m.group(1) not in custom_errors:
                    custom_errors.append(m.group(1))

        return custom_errors[:20]


register(ErrorHandlingAnalyzer())
