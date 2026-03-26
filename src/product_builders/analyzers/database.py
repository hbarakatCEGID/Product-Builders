"""Database & ORM Analyzer — Dimension 2 (CRITICAL).

Detects ORM, migration tool, database type, schema naming conventions,
migration directories, and seed data. This is CRITICAL because incorrect
database patterns in AI-generated code can cause data loss.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import SKIP_DIRS, BaseAnalyzer
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
    "mikro_orm": {
        "orm": "MikroORM",
        "deps": ["@mikro-orm/core"],
        "migration_tool": "mikro-orm",
        "migration_dir": "src/migrations",
    },
    "objection": {
        "orm": "Objection.js",
        "deps": ["objection"],
        "migration_tool": "knex",
        "migration_dir": "migrations",
    },
    "jooq": {
        "orm": "jOOQ",
        "deps": ["jooq"],
        "migration_tool": "flyway",
        "migration_dir": "src/main/resources/db/migration",
    },
    "mybatis": {
        "orm": "MyBatis",
        "deps": ["mybatis", "mybatis-spring-boot-starter"],
        "migration_tool": "flyway",
        "migration_dir": "src/main/resources/db/migration",
    },
    "ent": {
        "orm": "Ent",
        "deps": ["entgo.io/ent"],
        "migration_tool": "atlas",
        "migration_dir": "ent/migrate",
    },
    "sqlx_go": {
        "orm": "sqlx",
        "deps": ["github.com/jmoiron/sqlx"],
        "migration_tool": "golang-migrate",
        "migration_dir": "migrations",
    },
    "sqlc": {
        "orm": "sqlc",
        "deps": ["github.com/sqlc-dev/sqlc"],
        "migration_tool": "golang-migrate",
        "migration_dir": "migrations",
    },
    "dapper": {
        "orm": "Dapper",
        "deps": ["Dapper"],
        "migration_tool": "FluentMigrator",
        "migration_dir": "Migrations",
    },
    "exposed": {
        "orm": "Exposed",
        "deps": ["org.jetbrains.exposed"],
        "migration_tool": None,
        "migration_dir": None,
    },
    "peewee": {
        "orm": "Peewee",
        "deps": ["peewee"],
        "migration_tool": "peewee-migrate",
        "migration_dir": "migrations",
    },
    "sqlmodel": {
        "orm": "SQLModel",
        "deps": ["sqlmodel"],
        "migration_tool": "alembic",
        "migration_dir": "alembic/versions",
    },
    "gorm": {
        "orm": "GORM",
        "deps": ["gorm.io/gorm"],
        "migration_tool": "gorm-automigrate",
        "migration_dir": None,
    },
    "sequel": {
        "orm": "Sequel",
        "deps": ["sequel"],
        "migration_tool": "sequel",
        "migration_dir": "db/migrations",
    },
}

DB_TYPE_INDICATORS: dict[str, list[str]] = {
    "postgresql": [
        "pg", "postgres", "postgresql", "psycopg2", "psycopg", "Npgsql", "asyncpg",
        "@supabase/supabase-js", "@supabase/ssr", "supabase",
        "@neon/serverless", "@neondatabase/serverless",
    ],
    "mysql": ["mysql", "mysql2", "mysqlclient", "PyMySQL", "MySql.Data", "@planetscale/database"],
    "sqlite": ["sqlite3", "better-sqlite3", "sqlite", "Microsoft.Data.Sqlite"],
    "mongodb": ["mongoose", "mongodb", "pymongo", "Motor", "MongoDB.Driver"],
    "redis": ["redis", "ioredis", "aioredis"],
    "mssql": ["mssql", "tedious", "pyodbc", "Microsoft.Data.SqlClient"],
    "firebase": ["firebase", "firebase-admin", "@firebase/firestore"],
    "dynamodb": ["@aws-sdk/client-dynamodb", "boto3"],
    "cassandra": ["cassandra-driver", "gocql"],
    "cockroachdb": ["cockroachdb"],
    "turso": ["@libsql/client", "libsql"],
}


class DatabaseAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Database & ORM Analyzer"

    @property
    def dimension(self) -> str:
        return "database"

    def analyze(self, repo_path: Path, *, index=None) -> DatabaseResult:
        dep_names = self._collect_dep_names(repo_path)
        orm, orm_version, migration_tool, migration_dir = self._detect_orm(repo_path, dep_names)
        all_db_types = self._detect_all_db_types(dep_names)
        db_type = all_db_types[0] if all_db_types else None
        schema_naming = self._detect_schema_naming(repo_path, orm)
        has_seeds, seed_dir = self._detect_seeds(repo_path)
        relationship_patterns = self._detect_relationship_patterns(repo_path, orm)

        # Resolve actual migration directory
        actual_migration_dir = None
        if migration_dir:
            if "*" in migration_dir:
                candidates = [p for p in repo_path.glob(migration_dir) if p.is_dir()]
                if candidates:
                    # Prefer the app nearest repo root (stable choice when many */migrations exist)
                    def _migration_sort_key(p: Path) -> tuple[int, str]:
                        rel = p.relative_to(repo_path)
                        return (len(rel.parts), rel.as_posix().lower())

                    best = min(candidates, key=_migration_sort_key)
                    actual_migration_dir = str(best.relative_to(repo_path))
            elif (repo_path / migration_dir).is_dir():
                actual_migration_dir = migration_dir

        connection_pooling = self._detect_connection_pooling(repo_path, dep_names)
        schema_patterns = self._detect_schema_patterns(repo_path)

        result = DatabaseResult(
            status=AnalysisStatus.SUCCESS,
            database_type=db_type,
            database_types=all_db_types,
            orm=orm,
            orm_version=orm_version,
            migration_tool=migration_tool,
            migration_directory=actual_migration_dir,
            schema_naming_convention=schema_naming,
            relationship_patterns=relationship_patterns,
            has_seeds=has_seeds,
            seed_directory=seed_dir,
            connection_pooling=connection_pooling,
            schema_patterns=schema_patterns,
        )

        # Anti-pattern detection
        anti_patterns = []

        # ORM detected but no migrations
        if result.orm and not result.migration_directory:
            # Check if migration dir actually exists
            if result.migration_tool:
                anti_patterns.append("HIGH: ORM detected but no migration directory found")

        # No seed data
        if result.orm and not result.has_seeds:
            anti_patterns.append("LOW: no seed data detected — consider adding seeds for development")

        # No connection pooling for production DBs
        if result.database_type in ("postgresql", "mysql", "mssql") and not result.connection_pooling:
            anti_patterns.append("MEDIUM: no connection pooling detected for " + (result.database_type or "database"))

        result.anti_patterns = anti_patterns
        return result

    def _detect_connection_pooling(self, repo_path: Path, dep_names: set[str]) -> str | None:
        """Detect connection pooling tools."""
        if self.file_exists(repo_path, "pgbouncer.ini"):
            return "pgbouncer"
        pool_deps: dict[str, str] = {
            "pg-pool": "pg-pool",
            "@neondatabase/serverless": "neon-serverless",
        }
        for dep, name in pool_deps.items():
            if dep in dep_names:
                return name
        # Check for HikariCP in Spring config
        for cfg in (
            "src/main/resources/application.properties",
            "src/main/resources/application.yml",
        ):
            content = self.read_file(repo_path / cfg)
            if content and "hikari" in content.lower():
                return "hikaricp"
        return None

    def _detect_schema_patterns(self, repo_path: Path) -> list[str]:
        """Detect common schema patterns from model/migration files."""
        patterns: list[str] = []
        # Scan Prisma schema
        schema = self.read_file(repo_path / "prisma" / "schema.prisma")
        if schema:
            if "uuid()" in schema or "cuid()" in schema:
                patterns.append("uuid-primary-keys")
            if "deletedAt" in schema or "deleted_at" in schema or "isDeleted" in schema:
                patterns.append("soft-deletes")
            if "createdAt" in schema or "updatedAt" in schema or "@updatedAt" in schema:
                patterns.append("audit-timestamps")
            if "tenantId" in schema or "tenant_id" in schema or "organizationId" in schema:
                patterns.append("multi-tenancy")
        # Scan Django/SQLAlchemy models
        for pattern in ("**/models.py", "**/models/*.py"):
            for f in self.find_files(repo_path, pattern)[:10]:
                content = self.read_file(f)
                if not content:
                    continue
                if "UUIDField" in content or ("uuid" in content.lower() and "primary_key" in content):
                    if "uuid-primary-keys" not in patterns:
                        patterns.append("uuid-primary-keys")
                if "deleted_at" in content or "is_deleted" in content or "soft_delete" in content:
                    if "soft-deletes" not in patterns:
                        patterns.append("soft-deletes")
                if "auto_now_add" in content or "auto_now" in content or "created_at" in content:
                    if "audit-timestamps" not in patterns:
                        patterns.append("audit-timestamps")
        return patterns

    def _detect_orm(
        self, repo_path: Path, dep_names: set[str]
    ) -> tuple[str | None, str | None, str | None, str | None]:
        for key, info in ORM_INDICATORS.items():
            dep_list_raw = info.get("deps", [])
            if not isinstance(dep_list_raw, list):
                continue
            dep_list = dep_list_raw

            files_raw = info.get("files", [])
            files = files_raw if isinstance(files_raw, list) else []

            # Check config files first
            for f in files:
                if not isinstance(f, str):
                    continue
                if (repo_path / f).exists():
                    orm_name = info.get("orm")
                    if not isinstance(orm_name, str):
                        continue
                    mt = info.get("migration_tool")
                    md = info.get("migration_dir")
                    return orm_name, None, mt if isinstance(mt, str) else None, md if isinstance(md, str) else None

            # Check dependencies
            if any(dep in dep_names for dep in dep_list):
                orm_name = info.get("orm")
                if not isinstance(orm_name, str):
                    continue
                mt = info.get("migration_tool")
                md = info.get("migration_dir")
                return orm_name, None, mt if isinstance(mt, str) else None, md if isinstance(md, str) else None

        return None, None, None, None

    def _detect_db_type(self, dep_names: set[str]) -> str | None:
        for db_type, indicators in DB_TYPE_INDICATORS.items():
            if any(ind in dep_names for ind in indicators):
                return db_type
        return None

    def _detect_all_db_types(self, dep_names: set[str]) -> list[str]:
        """Detect ALL database types present (not just the first)."""
        found = []
        for db_type, indicators in DB_TYPE_INDICATORS.items():
            if any(ind in dep_names for ind in indicators):
                found.append(db_type)
        return found

    def _detect_relationship_patterns(self, repo_path: Path, orm: str | None) -> list[str]:
        """Lightweight markers for how models declare relations (templates / rules)."""
        found: list[str] = []
        prisma_schema = repo_path / "prisma" / "schema.prisma"
        if prisma_schema.exists():
            text = self.read_file(prisma_schema) or ""
            if re.search(r"@relation\s*\(", text):
                found.append("prisma-relations")
        if orm == "Django ORM":
            for p in repo_path.rglob("models.py"):
                if any(s in p.parts for s in SKIP_DIRS):
                    continue
                t = self.read_file(p)
                if t and (
                    "ForeignKey" in t
                    or "ManyToManyField" in t
                    or "OneToOneField" in t
                ):
                    found.append("django-orm-relations")
                    break
        scan_root = repo_path / "src" if (repo_path / "src").is_dir() else repo_path
        for path in scan_root.rglob("*.py"):
            if any(s in path.parts for s in SKIP_DIRS):
                continue
            t = self.read_file(path)
            if t and "relationship(" in t:
                found.append("sqlalchemy-relationship")
                break
        return list(dict.fromkeys(found))

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
