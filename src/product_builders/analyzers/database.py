"""Database & ORM Analyzer — Dimension 2 (CRITICAL).

Detects ORM, migration tool, database type, schema naming conventions,
migration directories, and seed data. This is CRITICAL because incorrect
database patterns in AI-generated code can cause data loss.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, DatabaseResult

ORM_INDICATORS: dict[str, dict[str, str | list[str]]] = {
    "prisma": {
        "orm": "Prisma",
        "files": ["prisma/schema.prisma"],
        "deps": ["prisma", "@prisma/client"],
        "migration_tool": "prisma migrate",
        "migration_dir": "prisma/migrations",
    },
    "typeorm": {
        "orm": "TypeORM",
        "deps": ["typeorm"],
        "migration_tool": "typeorm",
        "migration_dir": "src/migrations",
    },
    "sequelize": {
        "orm": "Sequelize",
        "deps": ["sequelize"],
        "migration_tool": "sequelize-cli",
        "migration_dir": "migrations",
    },
    "drizzle": {
        "orm": "Drizzle",
        "deps": ["drizzle-orm"],
        "migration_tool": "drizzle-kit",
        "migration_dir": "drizzle",
    },
    "knex": {
        "orm": "Knex",
        "deps": ["knex"],
        "migration_tool": "knex",
        "migration_dir": "migrations",
    },
    "mongoose": {
        "orm": "Mongoose",
        "deps": ["mongoose"],
        "migration_tool": None,
        "migration_dir": None,
    },
    "sqlalchemy": {
        "orm": "SQLAlchemy",
        "deps": ["sqlalchemy", "SQLAlchemy"],
        "migration_tool": "alembic",
        "migration_dir": "alembic/versions",
    },
    "alembic": {
        "orm": "SQLAlchemy",
        "deps": ["alembic"],
        "migration_tool": "alembic",
        "migration_dir": "alembic/versions",
    },
    "django_orm": {
        "orm": "Django ORM",
        "deps": ["django", "Django"],
        "migration_tool": "django",
        "migration_dir": "*/migrations",
    },
    "tortoise": {
        "orm": "Tortoise ORM",
        "deps": ["tortoise-orm"],
        "migration_tool": "aerich",
        "migration_dir": "migrations",
    },
    "hibernate": {
        "orm": "Hibernate",
        "deps": ["hibernate-core", "org.hibernate"],
        "migration_tool": "flyway",
        "migration_dir": "src/main/resources/db/migration",
    },
    "jpa": {
        "orm": "JPA",
        "deps": ["spring-boot-starter-data-jpa"],
        "migration_tool": "flyway",
        "migration_dir": "src/main/resources/db/migration",
    },
    "entity_framework": {
        "orm": "Entity Framework",
        "deps": ["Microsoft.EntityFrameworkCore"],
        "migration_tool": "ef-migrations",
        "migration_dir": "Migrations",
    },
    "active_record": {
        "orm": "Active Record",
        "deps": ["activerecord", "rails"],
        "migration_tool": "rails",
        "migration_dir": "db/migrate",
    },
}

DB_TYPE_INDICATORS: dict[str, list[str]] = {
    "postgresql": ["pg", "postgres", "postgresql", "psycopg2", "psycopg", "Npgsql", "asyncpg"],
    "mysql": ["mysql", "mysql2", "mysqlclient", "PyMySQL", "MySql.Data"],
    "sqlite": ["sqlite3", "better-sqlite3", "sqlite", "Microsoft.Data.Sqlite"],
    "mongodb": ["mongoose", "mongodb", "pymongo", "Motor", "MongoDB.Driver"],
    "redis": ["redis", "ioredis", "aioredis"],
    "mssql": ["mssql", "tedious", "pyodbc", "Microsoft.Data.SqlClient"],
}


class DatabaseAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Database & ORM Analyzer"

    @property
    def dimension(self) -> str:
        return "database"

    def analyze(self, repo_path: Path) -> DatabaseResult:
        dep_names = self._collect_dep_names(repo_path)
        orm, orm_version, migration_tool, migration_dir = self._detect_orm(repo_path, dep_names)
        db_type = self._detect_db_type(dep_names)
        schema_naming = self._detect_schema_naming(repo_path, orm)
        has_seeds, seed_dir = self._detect_seeds(repo_path)

        # Resolve actual migration directory
        actual_migration_dir = None
        if migration_dir:
            if "*" in migration_dir:
                candidates = list(repo_path.glob(migration_dir))
                if candidates:
                    actual_migration_dir = str(candidates[0].relative_to(repo_path))
            elif (repo_path / migration_dir).is_dir():
                actual_migration_dir = migration_dir

        return DatabaseResult(
            status=AnalysisStatus.SUCCESS,
            database_type=db_type,
            orm=orm,
            orm_version=orm_version,
            migration_tool=migration_tool,
            migration_directory=actual_migration_dir,
            schema_naming_convention=schema_naming,
            has_seeds=has_seeds,
            seed_directory=seed_dir,
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

        pom = repo_path / "pom.xml"
        if pom.exists():
            content = self.read_file(pom)
            if content:
                for m in re.finditer(r"<artifactId>([^<]+)</artifactId>", content):
                    deps.add(m.group(1))

        for csproj in self.find_files(repo_path, "*.csproj"):
            content = self.read_file(csproj)
            if content:
                for m in re.finditer(r'Include="([^"]+)"', content):
                    deps.add(m.group(1))

        gemfile = repo_path / "Gemfile"
        if gemfile.exists():
            content = self.read_file(gemfile)
            if content:
                for m in re.finditer(r"gem\s+['\"]([^'\"]+)['\"]", content):
                    deps.add(m.group(1))

        return deps

    def _detect_orm(
        self, repo_path: Path, dep_names: set[str]
    ) -> tuple[str | None, str | None, str | None, str | None]:
        for key, info in ORM_INDICATORS.items():
            dep_list = info.get("deps", [])
            assert isinstance(dep_list, list)

            # Check config files first
            files = info.get("files", [])
            assert isinstance(files, list)
            for f in files:
                if (repo_path / f).exists():
                    orm_name = info["orm"]
                    assert isinstance(orm_name, str)
                    mt = info.get("migration_tool")
                    md = info.get("migration_dir")
                    return orm_name, None, mt if isinstance(mt, str) else None, md if isinstance(md, str) else None

            # Check dependencies
            if any(dep in dep_names for dep in dep_list):
                orm_name = info["orm"]
                assert isinstance(orm_name, str)
                mt = info.get("migration_tool")
                md = info.get("migration_dir")
                return orm_name, None, mt if isinstance(mt, str) else None, md if isinstance(md, str) else None

        return None, None, None, None

    def _detect_db_type(self, dep_names: set[str]) -> str | None:
        for db_type, indicators in DB_TYPE_INDICATORS.items():
            if any(ind in dep_names for ind in indicators):
                return db_type
        return None

    def _detect_schema_naming(self, repo_path: Path, orm: str | None) -> str | None:
        if orm == "Prisma":
            schema = repo_path / "prisma" / "schema.prisma"
            if schema.exists():
                content = self.read_file(schema)
                if content:
                    models = re.findall(r"model\s+(\w+)", content)
                    if models:
                        if all(m[0].isupper() for m in models):
                            return "PascalCase"
        if orm in ("Django ORM", "SQLAlchemy", "Active Record"):
            return "snake_case"
        if orm in ("Entity Framework", "Hibernate", "JPA"):
            return "PascalCase"
        return None

    def _detect_seeds(self, repo_path: Path) -> tuple[bool, str | None]:
        seed_dirs = ["seeds", "seed", "db/seeds", "prisma/seed", "fixtures", "db/fixtures"]
        for sd in seed_dirs:
            if (repo_path / sd).is_dir():
                return True, sd

        seed_files = ["prisma/seed.ts", "prisma/seed.js", "db/seeds.rb", "seed.py"]
        for sf in seed_files:
            if (repo_path / sf).exists():
                return True, str(Path(sf).parent)

        return False, None


register(DatabaseAnalyzer())
