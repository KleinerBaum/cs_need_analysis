from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path


def _iter_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def build_index(*, source_dir: Path, out_dir: Path, version: str) -> None:
    target_dir = out_dir / version
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "esco_index.sqlite"
    manifest_path = target_dir / "manifest.json"

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

    for row in _iter_csv(occupations):
        cur.execute("INSERT OR REPLACE INTO concepts(uri, concept_type, code) VALUES(?, 'occupation', ?)", (row.get("conceptUri", ""), row.get("code", "")))
    for row in _iter_csv(skills):
        cur.execute("INSERT OR REPLACE INTO concepts(uri, concept_type, code) VALUES(?, 'skill', ?)", (row.get("conceptUri", ""), row.get("code", "")))
    for row in _iter_csv(labels):
        uri = row.get("conceptUri", "")
        lang = row.get("language", "en")
        label = row.get("preferredLabel", "") or row.get("label", "")
        if uri and label:
            cur.execute("INSERT INTO labels(uri, language, label) VALUES(?, ?, ?)", (uri, lang, label))
    for row in _iter_csv(relations):
        source = row.get("conceptUri", "")
        target = row.get("broaderUri", "")
        relation = row.get("relationType", "") or "related"
        if source and target:
            cur.execute("INSERT INTO relations(source_uri, relation, target_uri) VALUES(?, ?, ?)", (source, relation, target))

    conn.commit()
    conn.close()

    manifest = {
        "version": version,
        "sqlite": db_path.name,
        "source_dir": str(source_dir),
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
