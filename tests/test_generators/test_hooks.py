from __future__ import annotations

"""Tests for hooks generator blocked command filtering."""

from product_builders.profiles.base import filter_blocked_commands


def test_supabase_project_excludes_prisma_commands() -> None:
    """A Supabase project should not block prisma or alembic commands."""
    all_commands = [
        "prisma:migrate",
        "prisma:db push",
        "alembic upgrade",
        "alembic downgrade",
        "flyway migrate",
        "npm publish",
        "yarn publish",
        "docker build",
        "docker push",
        "rm -rf",
        "git push --force",
        "git push -f",
        "git reset --hard",
    ]
    detected_stack = {"@supabase/supabase-js", "next", "react"}
    filtered = filter_blocked_commands(all_commands, detected_stack)
    assert "prisma:migrate" not in filtered
    assert "prisma:db push" not in filtered
    assert "alembic upgrade" not in filtered
    assert "flyway migrate" not in filtered
    # Universal safety commands should remain
    assert "rm -rf" in filtered
    assert "git push --force" in filtered
    assert "npm publish" in filtered


def test_prisma_project_keeps_prisma_commands() -> None:
    """A Prisma project should still block prisma commands for non-engineers."""
    all_commands = ["prisma:migrate", "prisma:db push", "rm -rf"]
    detected_stack = {"prisma", "next", "react"}
    filtered = filter_blocked_commands(all_commands, detected_stack)
    assert "prisma:migrate" in filtered


def test_empty_stack_keeps_all_commands() -> None:
    """When no stack is detected, keep all blocked commands (safe default)."""
    all_commands = ["prisma:migrate", "rm -rf"]
    filtered = filter_blocked_commands(all_commands, set())
    assert filtered == all_commands
