"""Error Handling & Logging Analyzer — Dimension 5 (HIGH IMPACT).

Detects error handling strategy, logging framework, monitoring integration,
error response format, and custom error classes.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import MAX_SOURCE_FILES_ERROR_HANDLING, BaseAnalyzer
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
    "consola": ["consola"],
}

MONITORING_INDICATORS: dict[str, list[str]] = {
    "sentry": ["@sentry/node", "@sentry/react", "@sentry/browser", "sentry-sdk", "sentry_sdk", "Sentry"],
    "datadog": ["dd-trace", "datadog", "ddtrace"],
    "new-relic": ["newrelic", "new_relic_rpm"],
    "bugsnag": ["@bugsnag/js", "bugsnag"],
    "rollbar": ["rollbar"],
    "honeybadger": ["honeybadger", "@honeybadger-io/js"],
    "application-insights": ["applicationinsights", "Microsoft.ApplicationInsights"],
    "opentelemetry": ["@opentelemetry/api", "opentelemetry-api", "opentelemetry-sdk"],
    "grafana": ["@grafana/agent"],
}


class ErrorHandlingAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Error Handling & Logging Analyzer"

    @property
    def dimension(self) -> str:
        return "error_handling"

    def analyze(self, repo_path: Path, *, index=None) -> ErrorHandlingResult:
        dep_names = self._collect_dep_names(repo_path)
        all_logging = self._detect_all_logging_frameworks(dep_names, repo_path)
        logging_fw = all_logging[0] if all_logging else None
        logging_config = self._detect_logging_config(repo_path)
        monitoring = self._detect_monitoring(dep_names)
        error_strategy, error_format, custom_errors = self._detect_error_patterns_combined(
            repo_path
        )

        # Detect structured logging
        structured_logging = False
        structured_indicators = ["structlog", "pino", "@opentelemetry/api", "opentelemetry-sdk"]
        if any(ind in dep_names for ind in structured_indicators):
            structured_logging = True

        # AST-enriched path: find custom error/exception classes from AST
        if index is not None:
            all_classes = index.get_definitions(kind="class")
            for cls in all_classes:
                if cls.name.endswith(("Error", "Exception")):
                    if cls.name not in custom_errors:
                        custom_errors.append(cls.name)

        result = ErrorHandlingResult(
            status=AnalysisStatus.SUCCESS,
            error_strategy=error_strategy,
            logging_framework=logging_fw,
            logging_frameworks=all_logging,
            logging_config_file=logging_config,
            monitoring_integration=monitoring,
            error_response_format=error_format,
            custom_error_classes=custom_errors,
            structured_logging=structured_logging,
        )

        anti_patterns = []
        if result.error_strategy is None:
            anti_patterns.append("HIGH: no error handling strategy detected")
        if not result.structured_logging:
            anti_patterns.append("MEDIUM: no structured logging — log aggregation will be difficult")
        if result.monitoring_integration is None:
            anti_patterns.append("MEDIUM: no error monitoring integration (Sentry, Datadog, etc.)")
        result.anti_patterns = anti_patterns

        return result

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

        return None

    def _detect_all_logging_frameworks(self, dep_names: set[str], repo_path: Path) -> list[str]:
        """Detect ALL logging frameworks present (not just the first)."""
        found = []
        for fw, indicators in LOGGING_FRAMEWORK_INDICATORS.items():
            if fw == "python-logging":
                continue
            if any(ind in dep_names for ind in indicators):
                found.append(fw)
        # Check for Python stdlib logging usage
        if "python-logging" not in found:
            for py_file in self.find_files(repo_path, "src/**/*.py")[:10]:
                content = self.read_file(py_file)
                if content and "import logging" in content:
                    found.append("python-logging")
                    break
        # Fallback: detect console-based logging in TypeScript/JavaScript projects
        if not found:
            for ts_file in self.find_files(
                repo_path, "src/**/*.ts", "src/**/*.tsx", "src/**/*.js", "src/**/*.jsx"
            )[:10]:
                content = self.read_file(ts_file)
                if content and ("console.log(" in content or "console.error(" in content):
                    found.append("console")
                    break
        return found

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

    def _detect_error_patterns_combined(
        self, repo_path: Path
    ) -> tuple[str | None, str | None, list[str]]:
        """One repository pass for error strategy, JSON error responses, and custom error types."""
        strategy_ext = frozenset({
            ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".rs", ".go",
        })
        format_ext = frozenset({".ts", ".js", ".py", ".java", ".cs"})
        custom_ext = frozenset({".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs"})
        walk_ext = strategy_ext | custom_ext

        exception_count = 0
        result_type_count = 0
        error_format: str | None = None
        custom_errors: list[str] = []

        for path, content in self._iter_source_files(
            repo_path,
            extensions=walk_ext,
            max_files=MAX_SOURCE_FILES_ERROR_HANDLING,
        ):
            if path.suffix in strategy_ext:
                exception_count += (
                    content.count("throw ")
                    + content.count("raise ")
                    + content.count("throws ")
                )
                result_type_count += (
                    content.count("Result<")
                    + content.count("Either<")
                    + content.count("Result.Ok")
                )

            if error_format is None and path.suffix in format_ext:
                # Heuristic only: may match strings/comments; good enough for offline hints.
                if re.search(
                    r"(error|message|statusCode|status_code).*json",
                    content,
                    re.IGNORECASE,
                ):
                    error_format = "json"
                elif re.search(r"\.json\(\s*\{.*error", content, re.IGNORECASE):
                    error_format = "json"

            if path.suffix in custom_ext:
                for m in re.finditer(
                    r"class\s+(\w+Error)\s+extends\s+(?:Error|BaseError|HttpException)",
                    content,
                ):
                    if m.group(1) not in custom_errors:
                        custom_errors.append(m.group(1))

                for m in re.finditer(r"class\s+(\w+(?:Error|Exception))\s*\(", content):
                    if m.group(1) not in custom_errors:
                        custom_errors.append(m.group(1))

                for m in re.finditer(
                    r"class\s+(\w+Exception)\s+extends\s+\w+Exception",
                    content,
                ):
                    if m.group(1) not in custom_errors:
                        custom_errors.append(m.group(1))

        if result_type_count > exception_count and result_type_count > 0:
            strategy: str | None = "result-types"
        elif exception_count > 0:
            strategy = "exceptions"
        else:
            strategy = None

        return strategy, error_format, custom_errors[:20]


register(ErrorHandlingAnalyzer())
