from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable


def _iter_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _unique_existing(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    existing: list[Path] = []
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        existing.append(path)
    return existing


def _source_files(source_dir: Path, *names: str, glob_pattern: str) -> list[Path]:
    explicit_paths = [source_dir / name for name in names]
    globbed_paths = sorted(source_dir.glob(glob_pattern))
    return _unique_existing([*explicit_paths, *globbed_paths])


def _language_for_file(path: Path) -> str:
    match = re.search(r"_([a-z]{2})$", path.stem, flags=re.IGNORECASE)
    return match.group(1).lower() if match else "en"


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _iter_label_values(*values: str) -> Iterable[str]:
    for value in values:
        for label in re.split(r"[\n;|]+", str(value or "")):
            cleaned = " ".join(label.strip().split())
            if cleaned:
                yield cleaned


def _normalize_relation(value: str) -> str:
    relation = " ".join(str(value or "").strip().split())
    relation_name = re.split(r"[#/]", relation)[-1]
    normalized = (
        relation_name.casefold().replace("_", "").replace("-", "").replace(" ", "")
    )
    if normalized in {"essential", "essentialskill", "hasessentialskill"}:
        return "hasEssentialSkill"
    if normalized in {"optional", "optionalskill", "hasoptionalskill"}:
        return "hasOptionalSkill"
    if normalized in {"broader", "broadertransitive", "hasbroadertransitive"}:
        return "hasBroaderTransitive"
    return relation or "related"


def _relation_for_row(path: Path, row: dict[str, str]) -> str:
    relation = _first(row, "relationType", "relation")
    if relation:
        return relation
    if path.name.casefold().startswith("broaderrelations"):
        return "hasBroaderTransitive"
    return "related"


def build_index(*, source_dir: Path, out_dir: Path, version: str) -> None:
    normalized_dir = out_dir / "normalized" / version
    indexed_dir = out_dir / "indexed" / version
    normalized_dir.mkdir(parents=True, exist_ok=True)
    indexed_dir.mkdir(parents=True, exist_ok=True)
    db_path = indexed_dir / "esco_index.sqlite"
    manifest_path = indexed_dir / "manifest.json"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS concepts;
        DROP TABLE IF EXISTS labels;
        DROP TABLE IF EXISTS relations;
        CREATE TABLE concepts(uri TEXT PRIMARY KEY, concept_type TEXT NOT NULL, code TEXT DEFAULT '');
        CREATE TABLE labels(uri TEXT NOT NULL, language TEXT NOT NULL, label TEXT NOT NULL);
        CREATE TABLE relations(source_uri TEXT NOT NULL, relation TEXT NOT NULL, target_uri TEXT NOT NULL);
        CREATE INDEX idx_labels_lookup ON labels(language, label);
        CREATE INDEX idx_relations_lookup ON relations(source_uri, relation);
        """)

    occupation_files = _source_files(
        source_dir,
        "occupations_en.csv",
        "occupations.csv",
        glob_pattern="occupations_*.csv",
    )
    skill_files = _source_files(
        source_dir,
        "skills_en.csv",
        "skills.csv",
        glob_pattern="skills_*.csv",
    )
    label_files = _source_files(
        source_dir,
        "labels_en.csv",
        "labels.csv",
        glob_pattern="labels_*.csv",
    )
    relation_files = _source_files(
        source_dir,
        "broaderRelationsSkillPillar.csv",
        "broaderRelationsOccPillar.csv",
        "occupationSkillRelations.csv",
        glob_pattern="*Relations*.csv",
    )

    concept_rows: list[dict[str, str]] = []
    label_rows: list[dict[str, str]] = []
    relation_rows: list[dict[str, str]] = []
    seen_concepts: set[str] = set()
    seen_labels: set[tuple[str, str, str]] = set()
    seen_relations: set[tuple[str, str, str]] = set()

    def add_concept(uri: str, concept_type: str, code: str = "") -> None:
        if not uri:
            return
        if uri not in seen_concepts:
            concept_rows.append(
                {"uri": uri, "concept_type": concept_type, "code": code}
            )
            seen_concepts.add(uri)
        cur.execute(
            """
            INSERT OR REPLACE INTO concepts(uri, concept_type, code)
            VALUES(?, ?, ?)
            """,
            (uri, concept_type, code),
        )

    def add_label(uri: str, language: str, label: str) -> None:
        if not uri or not label:
            return
        key = (uri, language, label)
        if key in seen_labels:
            return
        seen_labels.add(key)
        label_rows.append({"uri": uri, "language": language, "label": label})
        cur.execute(
            "INSERT INTO labels(uri, language, label) VALUES(?, ?, ?)",
            (uri, language, label),
        )

    def add_relation(source_uri: str, relation: str, target_uri: str) -> None:
        if not source_uri or not target_uri:
            return
        normalized_relation = _normalize_relation(relation)
        key = (source_uri, normalized_relation, target_uri)
        if key in seen_relations:
            return
        seen_relations.add(key)
        relation_rows.append(
            {
                "source_uri": source_uri,
                "relation": normalized_relation,
                "target_uri": target_uri,
            }
        )
        cur.execute(
            """
            INSERT INTO relations(source_uri, relation, target_uri)
            VALUES(?, ?, ?)
            """,
            (source_uri, normalized_relation, target_uri),
        )

    for concept_type, files in (
        ("occupation", occupation_files),
        ("skill", skill_files),
    ):
        for path in files:
            language = _language_for_file(path)
            for row in _iter_csv(path):
                uri = _first(row, "conceptUri", "uri")
                code = _first(row, "code", "iscoGroup", "iscoCode")
                add_concept(uri, concept_type, code)
                row_language = _first(row, "language") or language
                for label in _iter_label_values(
                    _first(row, "preferredLabel", "label", "title"),
                    _first(row, "altLabels", "altLabel"),
                    _first(row, "hiddenLabels", "hiddenLabel"),
                ):
                    add_label(uri, row_language, label)

    for path in label_files:
        language = _language_for_file(path)
        for row in _iter_csv(path):
            uri = _first(row, "conceptUri", "uri")
            row_language = _first(row, "language") or language
            for label in _iter_label_values(
                _first(row, "preferredLabel", "label", "title"),
                _first(row, "altLabels", "altLabel"),
                _first(row, "hiddenLabels", "hiddenLabel"),
            ):
                add_label(uri, row_language, label)

    for path in relation_files:
        for row in _iter_csv(path):
            source = _first(row, "conceptUri", "sourceUri", "source", "occupationUri")
            target = _first(row, "broaderUri", "targetUri", "target", "skillUri")
            relation = _relation_for_row(path, row)
            add_relation(source, relation, target)

    conn.commit()
    conn.close()

    _write_csv(
        normalized_dir / "concepts.csv",
        ["uri", "concept_type", "code"],
        concept_rows,
    )
    _write_csv(normalized_dir / "labels.csv", ["uri", "language", "label"], label_rows)
    _write_csv(
        normalized_dir / "relations.csv",
        ["source_uri", "relation", "target_uri"],
        relation_rows,
    )

    source_files = [*occupation_files, *skill_files, *label_files, *relation_files]
    manifest = {
        "schema_version": 1,
        "layout_version": "esco_offline_build_v1",
        "version": version,
        "source_format": "official_esco_csv_compatible",
        "sqlite": db_path.name,
        "source_dir": str(source_dir),
        "normalized_dir": str(normalized_dir.relative_to(out_dir)),
        "indexed_dir": str(indexed_dir.relative_to(out_dir)),
        "generated_at": datetime.now(UTC).isoformat(),
        "languages": sorted({row["language"] for row in label_rows if row["language"]}),
        "counts": {
            "concepts": len(concept_rows),
            "labels": len(label_rows),
            "relations": len(relation_rows),
        },
        "source_files": [
            {
                "name": path.name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in source_files
            if path.exists()
        ],
        "normalized_files": [
            "concepts.csv",
            "labels.csv",
            "relations.csv",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out-dir", default=Path("data/esco_index"), type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build_index(source_dir=args.source_dir, out_dir=args.out_dir, version=args.version)


if __name__ == "__main__":
    main()
