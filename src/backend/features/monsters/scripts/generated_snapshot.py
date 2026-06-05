from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.inspection import inspect

from src.backend.core.database import get_manual_session_context
from src.backend.features.generation_ai.models import AIGenerationTask
from src.backend.infrastructure.generation_ai.task_documents import AI_GENERATION_TASK_DOCUMENTS_COLLECTION
from src.backend.infrastructure.mongo import get_mongo_provider
from src.backend.infrastructure.monsters import GeneratedClanORM, GeneratedMonsterORM, HabitatClanPoolEntryORM
from src.backend.infrastructure.monsters.actor_documents import GENERATED_MONSTER_ACTORS_COLLECTION

SNAPSHOT_VERSION = 1
SQL_DIR = "sql"
MONGO_DIR = "mongo"
MANIFEST_FILE = "manifest.json"


@dataclass(frozen=True, slots=True)
class SQLTableSpec:
    name: str
    model: type[Any]
    identity_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MongoCollectionSpec:
    name: str
    identity_fields: tuple[str, ...]
    conflict_fields: tuple[str, ...] = ()


@dataclass(slots=True)
class ImportReport:
    inserted: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)

    def record_inserted(self, name: str) -> None:
        self.inserted[name] = self.inserted.get(name, 0) + 1

    def record_skipped(self, name: str) -> None:
        self.skipped[name] = self.skipped.get(name, 0) + 1


SQL_TABLES: tuple[SQLTableSpec, ...] = (
    SQLTableSpec(
        name="generated_clans",
        model=GeneratedClanORM,
        identity_fields=("identity_hash",),
        conflict_fields=("id",),
    ),
    SQLTableSpec(
        name="generated_clan_members",
        model=GeneratedMonsterORM,
        identity_fields=("clan_id", "variant_id", "member_hash"),
        conflict_fields=("id", "mongo_actor_key"),
    ),
    SQLTableSpec(
        name="monster_habitat_clan_pool_entries",
        model=HabitatClanPoolEntryORM,
        identity_fields=("scope_type", "scope_id", "clan_identity_hash"),
        conflict_fields=("id",),
    ),
    SQLTableSpec(
        name="ai_generation_tasks",
        model=AIGenerationTask,
        identity_fields=("identity_key",),
        conflict_fields=("id",),
    ),
)

MONGO_COLLECTIONS: tuple[MongoCollectionSpec, ...] = (
    MongoCollectionSpec(
        name=GENERATED_MONSTER_ACTORS_COLLECTION,
        identity_fields=("mongo_actor_key",),
        conflict_fields=("_id", "member_id"),
    ),
    MongoCollectionSpec(
        name=AI_GENERATION_TASK_DOCUMENTS_COLLECTION,
        identity_fields=("document_kind", "task_id"),
        conflict_fields=("_id",),
    ),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export/import generated monster content snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export generated monster SQL and Mongo data.")
    export_parser.add_argument("--out", required=True, help="Output snapshot directory.")

    import_parser = subparsers.add_parser("import", help="Import generated monster SQL and Mongo data.")
    import_parser.add_argument("--in", dest="input", required=True, help="Input snapshot directory.")
    import_parser.add_argument("--dry-run", action="store_true", help="Validate and compare without inserting.")

    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    if options.command == "export":
        manifest = await export_snapshot(Path(options.out))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return
    if options.command == "import":
        report = await import_snapshot(Path(options.input), dry_run=bool(options.dry_run))
        print(json.dumps(_report_payload(report, dry_run=bool(options.dry_run)), ensure_ascii=False, indent=2))
        if report.conflicts:
            raise SystemExit(2)
        return
    raise ValueError(f"Unsupported generated snapshot command: {options.command}")


async def export_snapshot(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    (root / SQL_DIR).mkdir(exist_ok=True)
    (root / MONGO_DIR).mkdir(exist_ok=True)

    counts: dict[str, int] = {}
    async with get_manual_session_context() as session:
        for spec in SQL_TABLES:
            rows = await session.scalars(select(spec.model).order_by(*_order_columns(spec)))
            payloads = [_model_to_payload(row) for row in rows.all()]
            _write_jsonl(root / SQL_DIR / f"{spec.name}.jsonl", payloads)
            counts[f"sql.{spec.name}"] = len(payloads)

    database = get_mongo_provider().database()
    for spec in MONGO_COLLECTIONS:
        documents: list[dict[str, Any]] = []
        cursor = database[spec.name].find({}).sort("_id", 1)
        async for document in cursor:
            documents.append(dict(document))
        _write_jsonl(root / MONGO_DIR / f"{spec.name}.jsonl", documents)
        counts[f"mongo.{spec.name}"] = len(documents)

    manifest = {
        "snapshot_version": SNAPSHOT_VERSION,
        "content_kind": "generated_monster_content",
        "exported_at": datetime.now().astimezone().isoformat(),
        "counts": counts,
        "sql_tables": [spec.name for spec in SQL_TABLES],
        "mongo_collections": [spec.name for spec in MONGO_COLLECTIONS],
    }
    (root / MANIFEST_FILE).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


async def import_snapshot(root: Path, *, dry_run: bool = False) -> ImportReport:
    _validate_manifest(root)
    report = ImportReport()
    sql_inserts: list[tuple[SQLTableSpec, dict[str, Any]]] = []
    mongo_inserts: list[tuple[MongoCollectionSpec, dict[str, Any]]] = []

    async with get_manual_session_context() as session:
        for spec in SQL_TABLES:
            for payload in _read_jsonl(root / SQL_DIR / f"{spec.name}.jsonl"):
                existing = await _find_existing_sql_row(session, spec, payload)
                if existing is None:
                    sql_inserts.append((spec, payload))
                    report.record_inserted(f"sql.{spec.name}")
                    continue
                if _same_payload(_model_to_payload(existing), payload):
                    report.record_skipped(f"sql.{spec.name}")
                    continue
                report.conflicts.append(_conflict_message("sql", spec.name, spec.identity_fields, payload))

        database = get_mongo_provider().database()
        for spec in MONGO_COLLECTIONS:
            collection = database[spec.name]
            for payload in _read_jsonl(root / MONGO_DIR / f"{spec.name}.jsonl"):
                document = _decode_payload(payload)
                existing = await _find_existing_mongo_document(collection, spec, document)
                if existing is None:
                    mongo_inserts.append((spec, document))
                    report.record_inserted(f"mongo.{spec.name}")
                    continue
                if _same_payload(existing, document):
                    report.record_skipped(f"mongo.{spec.name}")
                    continue
                report.conflicts.append(_conflict_message("mongo", spec.name, spec.identity_fields, document))

        if report.conflicts or dry_run:
            await session.rollback()
            return report

        for spec, payload in sql_inserts:
            session.add(spec.model(**_decode_payload(payload)))
        await session.commit()

    database = get_mongo_provider().database()
    for spec, document in mongo_inserts:
        await database[spec.name].insert_one(document)
    return report


def _validate_manifest(root: Path) -> None:
    manifest_path = root / MANIFEST_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"Generated snapshot manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("snapshot_version") or 0) != SNAPSHOT_VERSION:
        raise ValueError(f"Unsupported generated snapshot version: {manifest.get('snapshot_version')}")
    if manifest.get("content_kind") != "generated_monster_content":
        raise ValueError(f"Unsupported generated snapshot content_kind: {manifest.get('content_kind')}")


def _model_to_payload(row: Any) -> dict[str, Any]:
    return {attr.key: _encode_value(getattr(row, attr.key)) for attr in inspect(type(row)).column_attrs}


def _order_columns(spec: SQLTableSpec) -> list[Any]:
    return [getattr(spec.model, field) for field in (*spec.identity_fields, *spec.conflict_fields)]


async def _find_existing_sql_row(session: Any, spec: SQLTableSpec, payload: dict[str, Any]) -> Any | None:
    decoded = _decode_payload(payload)
    for fields in (spec.identity_fields, *[(field_name,) for field_name in spec.conflict_fields]):
        if not fields or any(decoded.get(field_name) in (None, "") for field_name in fields):
            continue
        stmt = select(spec.model)
        for field_name in fields:
            stmt = stmt.where(getattr(spec.model, field_name) == decoded[field_name])
        row = await session.scalar(stmt)
        if row is not None:
            return row
    return None


async def _find_existing_mongo_document(
    collection: Any, spec: MongoCollectionSpec, document: dict[str, Any]
) -> dict[str, Any] | None:
    for fields in (spec.identity_fields, *[(field_name,) for field_name in spec.conflict_fields]):
        if not fields or any(document.get(field_name) in (None, "") for field_name in fields):
            continue
        existing = await collection.find_one({field_name: document[field_name] for field_name in fields})
        if isinstance(existing, dict):
            return dict(existing)
    return None


def _same_payload(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canonical(left) == _canonical(right)


def _canonical(payload: dict[str, Any]) -> str:
    normalized = {
        key: value for key, value in _encode_value(payload).items() if key not in {"created_at", "updated_at"}
    }
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _conflict_message(kind: str, name: str, identity_fields: tuple[str, ...], payload: dict[str, Any]) -> str:
    identity = ", ".join(f"{field}={payload.get(field)!r}" for field in identity_fields)
    return f"{kind}.{name} conflict for {identity}"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(_encode_value(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _encode_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, UUID):
        return {"$uuid": str(value)}
    if isinstance(value, dict):
        return {str(key): _encode_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_encode_value(inner) for inner in value]
    if isinstance(value, tuple):
        return [_encode_value(inner) for inner in value]
    return value


def _decode_payload(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$datetime"}:
            return datetime.fromisoformat(str(value["$datetime"]))
        if set(value) == {"$uuid"}:
            return UUID(str(value["$uuid"]))
        return {key: _decode_payload(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_decode_payload(inner) for inner in value]
    return value


def _report_payload(report: ImportReport, *, dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "inserted": dict(sorted(report.inserted.items())),
        "skipped": dict(sorted(report.skipped.items())),
        "conflict_count": len(report.conflicts),
        "conflicts": report.conflicts,
    }


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
