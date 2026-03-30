from __future__ import annotations

"""Tests for ErrorHandlingAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.error_handling import ErrorHandlingAnalyzer


def test_detects_exceptions_strategy(tmp_path: Path) -> None:
    """Files with throw/try/catch should detect 'exceptions' error strategy."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.ts").write_text(
        "function doWork() {\n"
        "  throw new Error('boom');\n"
        "}\n"
        "try {\n"
        "  doWork();\n"
        "} catch (e) {\n"
        "  console.error(e);\n"
        "}\n"
    )
    (src / "handler.ts").write_text(
        "function handle() {\n"
        "  throw new Error('fail');\n"
        "}\n"
    )

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.error_strategy == "exceptions"


def test_detects_result_types_strategy(tmp_path: Path) -> None:
    """Files with Result<> patterns should detect 'result-types' strategy when dominant."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.ts").write_text(
        "type Result<T> = Ok<T> | Err;\n"
        "function parse(): Result<Data> { return Result.Ok(data); }\n"
        "function validate(): Result<Data> { return Result.Ok(data); }\n"
        "function transform(): Result<Data> { return Result.Ok(data); }\n"
        "function process(): Result<Data> { return Result.Ok(data); }\n"
    )

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.error_strategy == "result-types"


def test_detects_winston_logging(tmp_path: Path) -> None:
    """package.json with winston should detect it as logging framework."""
    pkg = {"dependencies": {"winston": "^3.10.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.logging_framework == "winston"


def test_detects_python_logging(tmp_path: Path) -> None:
    """Python file with 'import logging' should detect python-logging."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("import logging\nlogger = logging.getLogger(__name__)\n")

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.logging_framework == "python-logging"


def test_detects_sentry_monitoring(tmp_path: Path) -> None:
    """package.json with @sentry/node should detect sentry monitoring."""
    pkg = {"dependencies": {"@sentry/node": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.monitoring_integration == "sentry"


def test_detects_custom_error_classes(tmp_path: Path) -> None:
    """File with 'class ApiError extends Error' should detect custom error class."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "errors.ts").write_text(
        "export class ApiError extends Error {\n"
        "  constructor(public statusCode: number, message: string) {\n"
        "    super(message);\n"
        "  }\n"
        "}\n"
    )

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "ApiError" in result.custom_error_classes


def test_detects_multiple_logging_frameworks(tmp_path: Path) -> None:
    """package.json with winston and pino should detect both in logging_frameworks."""
    pkg = {"dependencies": {"winston": "^3.10.0", "pino": "^8.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "winston" in result.logging_frameworks
    assert "pino" in result.logging_frameworks


def test_empty_repo_no_errors(tmp_path: Path) -> None:
    """Empty repo should return success with no error strategy."""
    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.status.value == "success"
    assert result.error_strategy is None


def test_anti_pattern_no_error_handling(tmp_path: Path) -> None:
    """Empty repo should trigger 'no error handling strategy' anti-pattern."""
    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no error handling strategy" in ap for ap in result.anti_patterns)


def test_anti_pattern_no_monitoring(tmp_path: Path) -> None:
    """Repo with error handling but no monitoring should trigger anti-pattern."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.ts").write_text(
        "function doWork() {\n"
        "  throw new Error('boom');\n"
        "}\n"
    )

    analyzer = ErrorHandlingAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no error monitoring" in ap for ap in result.anti_patterns)
