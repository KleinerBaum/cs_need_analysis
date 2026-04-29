from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OfflineEscoIndex:
    version: str
    sqlite_path: Path
    manifest_path: Path

    @classmethod
    def load(cls, base_dir: Path, version: str) -> "OfflineEscoIndex | None":
        index_dir = base_dir / version
        sqlite_path = index_dir / "esco_index.sqlite"
        manifest_path = index_dir / "manifest.json"
        if not sqlite_path.exists() or not manifest_path.exists():
            return None
        return cls(version=version, sqlite_path=sqlite_path, manifest_path=manifest_path)

    def _query_json(self, query: str, params: tuple[object, ...]) -> list[dict[str, Any]]:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def search(self, *, text: str, type_name: str, language: str, limit: int) -> dict[str, Any]:
        pattern = f"%{text.strip().lower()}%"
        rows = self._query_json(
            """
            SELECT c.uri, l.label, c.concept_type as conceptType
            FROM concepts c
            JOIN labels l ON c.uri = l.uri
            WHERE l.language = ? AND c.concept_type = ? AND lower(l.label) LIKE ?
            ORDER BY l.label
            LIMIT ?
            """,
            (language, type_name, pattern, limit),
        )
        return {"_embedded": {"results": rows}, "total": len(rows)}

    def terms(self, *, uri: str, type_name: str, language: str) -> dict[str, Any]:
        del type_name
        rows = self._query_json(
            "SELECT uri, language, label FROM labels WHERE uri = ? AND language = ?",
            (uri, language),
        )
        if not rows:
            rows = self._query_json("SELECT uri, language, label FROM labels WHERE uri = ?", (uri,))
        return {"_embedded": {"results": rows}, "total": len(rows)}

    def resource_occupation(self, *, uri: str, language: str) -> dict[str, Any]:
        concept_rows = self._query_json(
            "SELECT uri, code, concept_type FROM concepts WHERE uri = ? AND concept_type = 'occupation'",
            (uri,),
        )
        if not concept_rows:
            return {}
        label_rows = self._query_json(
            "SELECT label FROM labels WHERE uri = ? AND language = ? LIMIT 1",
            (uri, language),
        )
        title = label_rows[0]["label"] if label_rows else ""
        return {
            "uri": uri,
            "code": concept_rows[0].get("code", ""),
            "title": title,
            "preferredLabel": {language: title},
            "version": self.version,
        }

    def resource_related(self, *, uri: str, relation: str, language: str) -> dict[str, Any]:
        rows = self._query_json(
            """
            SELECT r.target_uri as uri, l.label
            FROM relations r
            LEFT JOIN labels l ON r.target_uri = l.uri AND l.language = ?
            WHERE r.source_uri = ? AND r.relation = ?
            ORDER BY l.label
            """,
            (language, uri, relation),
        )
        return {"_embedded": {"results": rows}, "total": len(rows)}


def read_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))
