from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone


RAW_NAME_RE = re.compile(r"^(?P<schema>raw_pe_(?:master|portal))\.(?P<table>[A-Za-z0-9_]+)\.csv$")


def quote_name(alias: str, name: str) -> str:
    return connections[alias].ops.quote_name(name)


def normalize_column_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", str(name or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "unnamed_column"
    if cleaned[0].isdigit():
        cleaned = f"col_{cleaned}"
    return cleaned[:64]


def row_hash(schema: str, table: str, row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{schema}.{table}:{payload}".encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = "Idempotently ingest raw PE master/portal CSV files into raw_pe_master/raw_pe_portal schemas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="/Users/inditech-tech/Desktop/PELocalMasterNewCSVS",
            help="Folder containing files named raw_pe_master.<table>.csv and raw_pe_portal.<table>.csv.",
        )
        parser.add_argument("--database", default="default", help="Django DB alias used for the MySQL connection.")
        parser.add_argument(
            "--create-schemas",
            action="store_true",
            help="Attempt to CREATE DATABASE for raw schemas. Requires privileges.",
        )
        parser.add_argument(
            "--allow-duplicate-source-ids",
            action="store_true",
            help=(
                "Drop existing PRIMARY KEY constraints on raw staging tables when possible so "
                "duplicate source IDs from extract files are preserved by __row_hash."
            ),
        )

    def handle(self, *args, **options):
        base = Path(options["path"])
        if not base.exists():
            raise CommandError(f"CSV folder not found: {base}")

        alias = options["database"]
        files = sorted(base.glob("raw_pe_*.*.csv"))
        if not files:
            raise CommandError(f"No raw PE CSV files found in {base}")

        self._allow_duplicate_source_ids = options["allow_duplicate_source_ids"]
        totals: dict[str, dict[str, int]] = {}
        for path in files:
            match = RAW_NAME_RE.match(path.name)
            if not match:
                self.stdout.write(self.style.WARNING(f"Skipping unexpected file name: {path.name}"))
                continue
            schema = match.group("schema")
            table = match.group("table")
            stats = self.ingest_file(alias, path, schema, table, create_schema=options["create_schemas"])
            totals[f"{schema}.{table}"] = stats

        self.stdout.write(self.style.SUCCESS("Raw PE CSV ingestion complete."))
        for table_name in sorted(totals):
            stats = totals[table_name]
            self.stdout.write(
                f"{table_name}: read={stats['read']} inserted={stats['inserted']} skipped={stats['skipped']}"
            )

    def ingest_file(self, alias: str, path: Path, schema: str, table: str, *, create_schema: bool) -> dict[str, int]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            source_headers = reader.fieldnames or []
            if not source_headers:
                return {"read": 0, "inserted": 0, "skipped": 0}
            column_map = self.unique_column_map(source_headers)

            self.ensure_schema(alias, schema, create_schema=create_schema)
            self.ensure_table(alias, schema, table, column_map.values())
            if self.allow_duplicate_source_ids:
                self.drop_primary_key(alias, schema, table)
            self.ensure_missing_columns(alias, schema, table, column_map.values())
            self.relax_required_columns_not_in_csv(alias, schema, table, set(column_map.values()))

            read = inserted = skipped = 0
            for index, row in enumerate(reader, start=2):
                read += 1
                normalized_row = {column_map[key]: (value if value != "" else None) for key, value in row.items()}
                normalized_row["__row_hash"] = row_hash(schema, table, row)
                normalized_row["__csv_file_name"] = path.name
                normalized_row["__csv_row_number"] = index
                normalized_row["__loaded_at"] = timezone.now()
                normalized_row.update(self.required_insert_defaults(alias, schema, table, normalized_row, index))
                was_inserted = self.insert_ignore(alias, schema, table, normalized_row)
                if was_inserted:
                    inserted += 1
                else:
                    skipped += 1
        return {"read": read, "inserted": inserted, "skipped": skipped}

    @property
    def allow_duplicate_source_ids(self) -> bool:
        return bool(getattr(self, "_allow_duplicate_source_ids", False))

    def unique_column_map(self, headers: list[str]) -> dict[str, str]:
        used: dict[str, int] = {}
        mapped: dict[str, str] = {}
        for header in headers:
            base = normalize_column_name(header)
            count = used.get(base, 0)
            used[base] = count + 1
            mapped[header] = base if count == 0 else f"{base}_{count + 1}"[:64]
        return mapped

    def ensure_schema(self, alias: str, schema: str, *, create_schema: bool) -> None:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", [schema])
            exists = cursor.fetchone() is not None
            if exists:
                return
            if not create_schema:
                raise CommandError(f"Schema {schema} does not exist. Create it first or pass --create-schemas.")
            cursor.execute(
                f"CREATE DATABASE {quote_name(alias, schema)} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

    def ensure_table(self, alias: str, schema: str, table: str, columns: Any) -> None:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                LIMIT 1
                """,
                [schema, table],
            )
            if cursor.fetchone() is not None:
                return

            column_sql = [f"{quote_name(alias, column)} longtext NULL" for column in columns]
            column_sql.extend(
                [
                    "`__row_hash` varchar(64) NOT NULL",
                    "`__csv_file_name` varchar(255) NOT NULL",
                    "`__csv_row_number` bigint NOT NULL",
                    "`__loaded_at` datetime(6) NOT NULL",
                    "UNIQUE KEY `raw_csv_row_hash_uniq` (`__row_hash`)",
                ]
            )
            cursor.execute(
                f"CREATE TABLE {quote_name(alias, schema)}.{quote_name(alias, table)} "
                f"({', '.join(column_sql)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )

    def drop_primary_key(self, alias: str, schema: str, table: str) -> None:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND CONSTRAINT_TYPE = 'PRIMARY KEY'
                LIMIT 1
                """,
                [schema, table],
            )
            if cursor.fetchone() is None:
                return
            try:
                cursor.execute(f"ALTER TABLE {quote_name(alias, schema)}.{quote_name(alias, table)} DROP PRIMARY KEY")
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not drop primary key on {schema}.{table}; continuing with INSERT IGNORE: {exc}"
                    )
                )

    def table_columns(self, alias: str, schema: str, table: str) -> dict[str, dict[str, Any]]:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                [schema, table],
            )
            return {
                row[0]: {
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                    "extra": row[4] or "",
                    "key": row[5] or "",
                }
                for row in cursor.fetchall()
            }

    def ensure_missing_columns(self, alias: str, schema: str, table: str, columns: Any) -> None:
        existing = self.table_columns(alias, schema, table)
        needed = list(columns) + ["__row_hash", "__csv_file_name", "__csv_row_number", "__loaded_at"]
        with connections[alias].cursor() as cursor:
            for column in needed:
                if column in existing:
                    continue
                if column == "__row_hash":
                    column_type = "varchar(64) NULL"
                elif column == "__csv_file_name":
                    column_type = "varchar(255) NULL"
                elif column == "__csv_row_number":
                    column_type = "bigint NULL"
                elif column == "__loaded_at":
                    column_type = "datetime(6) NULL"
                else:
                    column_type = "longtext NULL"
                cursor.execute(
                    f"ALTER TABLE {quote_name(alias, schema)}.{quote_name(alias, table)} "
                    f"ADD COLUMN {quote_name(alias, column)} {column_type}"
                )
            if "__row_hash" not in existing:
                try:
                    cursor.execute(
                        f"ALTER TABLE {quote_name(alias, schema)}.{quote_name(alias, table)} "
                        "ADD UNIQUE KEY `raw_csv_row_hash_uniq` (`__row_hash`)"
                    )
                except Exception:
                    pass

    def relax_required_columns_not_in_csv(self, alias: str, schema: str, table: str, csv_columns: set[str]) -> None:
        existing = self.table_columns(alias, schema, table)
        metadata = {"__row_hash", "__csv_file_name", "__csv_row_number", "__loaded_at"}
        with connections[alias].cursor() as cursor:
            for column, info in existing.items():
                if column in csv_columns or column in metadata:
                    continue
                if info["nullable"] or info["default"] is not None or "auto_increment" in info["extra"].lower():
                    continue
                if info["key"] == "PRI":
                    continue
                cursor.execute(
                    f"ALTER TABLE {quote_name(alias, schema)}.{quote_name(alias, table)} "
                    f"MODIFY COLUMN {quote_name(alias, column)} {info['type']} NULL"
                )

    def required_insert_defaults(
        self,
        alias: str,
        schema: str,
        table: str,
        row: dict[str, Any],
        row_number: int,
    ) -> dict[str, Any]:
        defaults: dict[str, Any] = {}
        existing = self.table_columns(alias, schema, table)
        for column, info in existing.items():
            if column in row:
                continue
            if info["nullable"] or info["default"] is not None or "auto_increment" in info["extra"].lower():
                continue
            if info["key"] == "PRI" and column == "id":
                defaults[column] = row_number - 1
            elif info["type"].lower().startswith(("bigint", "int", "smallint", "tinyint")):
                defaults[column] = 0
            elif info["type"].lower().startswith("datetime"):
                defaults[column] = timezone.now()
            else:
                defaults[column] = ""
        return defaults

    def insert_ignore(self, alias: str, schema: str, table: str, row: dict[str, Any]) -> bool:
        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_sql = ", ".join(quote_name(alias, column) for column in columns)
        sql = (
            f"INSERT IGNORE INTO {quote_name(alias, schema)}.{quote_name(alias, table)} "
            f"({column_sql}) VALUES ({placeholders})"
        )
        with connections[alias].cursor() as cursor:
            cursor.execute(sql, [row[column] for column in columns])
            return cursor.rowcount == 1
