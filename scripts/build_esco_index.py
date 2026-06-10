from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
from pathlib import Path


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


def build_index(*, source_dir: Path, out_dir: Path, version: str) -> None:
    normalized_dir = out_dir / "normalized" / version
    indexed_dir = out_dir / "indexed" / version
    normalized_dir.mkdir(parents=True, exist_ok=True)
    indexed_dir.mkdir(parents=True, exist_ok=True)
    db_path = indexed_dir / "esco_index.sqlite"
    manifest_path = indexed_dir / "manifest.json"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS concepts;
        DROP TABLE IF EXISTS labels;
        DROP TABLE IF EXISTS relations;
        CREATE TABLE concepts(uri TEXT PRIMARY KEY, concept_type TEXT NOT NULL, code TEXT DEFAULT '');
        CREATE TABLE labels(uri TEXT NOT NULL, language TEXT NOT NULL, label TEXT NOT NULL);
        CREATE TABLE relations(source_uri TEXT NOT NULL, relation TEXT NOT NULL, target_uri TEXT NOT NULL);
        CREATE INDEX idx_labels_lookup ON labels(language, label);
        CREATE INDEX idx_relations_lookup ON relations(source_uri, relation);
        """
    )

    occupations = source_dir / "occupations_en.csv"
    skills = source_dir / "skills_en.csv"
    labels = source_dir / "labels_en.csv"
    relations = source_dir / "broaderRelationsSkillPillar.csv"

    concept_rows: list[dict[str, str]] = []
    label_rows: list[dict[str, str]] = []
    relation_rows: list[dict[str, str]] = []

    for row in _iter_csv(occupations):
        uri = row.get("conceptUri", "")
        code = row.get("code", "")
        concept_rows.append({"uri": uri, "concept_type": "occupation", "code": code})
        cur.execute(
            "INSERT OR REPLACE INTO concepts(uri, concept_type, code) VALUES(?, 'occupation', ?)",
            (uri, code),
        )
    for row in _iter_csv(skills):
        uri = row.get("conceptUri", "")
        code = row.get("code", "")
        concept_rows.append({"uri": uri, "concept_type": "skill", "code": code})
        cur.execute(
            "INSERT OR REPLACE INTO concepts(uri, concept_type, code) VALUES(?, 'skill', ?)",
            (uri, code),
        )
    for row in _iter_csv(labels):
        uri = row.get("conceptUri", "")
        lang = row.get("language", "en")
        label = row.get("preferredLabel", "") or row.get("label", "")
        if uri and label:
            label_rows.append({"uri": uri, "language": lang, "label": label})
            cur.execute("INSERT INTO labels(uri, language, label) VALUES(?, ?, ?)", (uri, lang, label))
    for row in _iter_csv(relations):
        source = row.get("conceptUri", "")
        target = row.get("broaderUri", "")
        relation = row.get("relationType", "") or "related"
        if source and target:
            relation_rows.append(
                {"source_uri": source, "relation": relation, "target_uri": target}
            )
            cur.execute("INSERT INTO relations(source_uri, relation, target_uri) VALUES(?, ?, ?)", (source, relation, target))

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

    source_files = [occupations, skills, labels, relations]
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
