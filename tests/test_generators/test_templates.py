"""Tests for Jinja2 template rendering correctness."""
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from product_builders.models.analysis import TestingResult
from product_builders.models.profile import ProductMetadata, ProductProfile


def _render_testing_template(profile: ProductProfile) -> str:
    """Render the testing.mdc template with the given profile."""
    template_dir = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "product_builders"
        / "generators"
        / "templates"
    )
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    tmpl = env.get_template("testing.mdc.j2")
    return tmpl.render(profile=profile, company_standards={})


def test_testing_rules_numbered_sequentially_when_all_present() -> None:
    """When all optional fields are present, rules should be 1 through N."""
    profile = ProductProfile(
        metadata=ProductMetadata(name="test"),
        testing=TestingResult(
            test_framework="vitest",
            test_runner="vitest",
            test_file_pattern="**/*.test.ts",
            test_directories=["tests"],
            e2e_framework="playwright",
        ),
    )
    content = _render_testing_template(profile)
    numbers = re.findall(r"^(\d+)\.", content, re.MULTILINE)
    # Should be sequential: 1, 2, 3, 4, 5, 6 (or more)
    for i, n in enumerate(numbers, 1):
        assert n == str(i), f"Expected rule {i} but got {n}"


def test_testing_rules_numbered_sequentially_when_optional_missing() -> None:
    """When test_file_pattern and test_directories are absent, no numbering gaps."""
    profile = ProductProfile(
        metadata=ProductMetadata(name="test"),
        testing=TestingResult(test_framework="vitest", test_runner="vitest"),
    )
    content = _render_testing_template(profile)
    numbers = re.findall(r"^(\d+)\.", content, re.MULTILINE)
    # Should be sequential regardless of how many rules are included
    for i, n in enumerate(numbers, 1):
        assert n == str(i), f"Expected rule {i} but got {n}"
