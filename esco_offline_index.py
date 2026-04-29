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

    def _resolve_label(self, *, uri: str, language: str) -> str:
        rows = self._query_json(
            "SELECT label FROM labels WHERE uri = ? AND language = ? LIMIT 1",
            (uri, language),
        )
        if rows:
            return str(rows[0].get("label") or "").strip()
        fallback_rows = self._query_json(
            "SELECT label FROM labels WHERE uri = ? LIMIT 1",
            (uri,),
        )
        return str(fallback_rows[0].get("label") or "").strip() if fallback_rows else ""

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
        results = [
            {
                "uri": str(row.get("uri") or "").strip(),
                "title": str(row.get("label") or "").strip(),
                "label": str(row.get("label") or "").strip(),
                "preferredLabel": str(row.get("label") or "").strip(),
                "conceptType": str(row.get("conceptType") or type_name).strip().lower() or type_name,
                "type": str(row.get("conceptType") or type_name).strip().lower() or type_name,
            }
            for row in rows
        ]
        return {"_embedded": {"results": results}, "total": len(results)}

    def suggest2(self, *, text: str, type_name: str, language: str, limit: int) -> dict[str, Any]:
        return self.search(text=text, type_name=type_name, language=language, limit=limit)

    def terms(self, *, uri: str, type_name: str, language: str) -> dict[str, Any]:
        rows = self._query_json(
            """
            SELECT l.uri, l.language, l.label, c.concept_type as conceptType
            FROM labels l
            LEFT JOIN concepts c ON l.uri = c.uri
            WHERE l.uri = ? AND l.language = ?
            """,
            (uri, language),
        )
        if not rows:
            rows = self._query_json(
                """
                SELECT l.uri, l.language, l.label, c.concept_type as conceptType
                FROM labels l
                LEFT JOIN concepts c ON l.uri = c.uri
                WHERE l.uri = ?
                """,
                (uri,),
            )
        concept_type = type_name.strip().lower() or "occupation"
        results = [
            {
                "uri": str(row.get("uri") or "").strip(),
                "language": str(row.get("language") or language).strip() or language,
                "title": str(row.get("label") or "").strip(),
                "label": str(row.get("label") or "").strip(),
                "preferredLabel": str(row.get("label") or "").strip(),
                "conceptType": str(row.get("conceptType") or concept_type).strip().lower()
                or concept_type,
            }
            for row in rows
        ]
        return {"_embedded": {"results": results}, "total": len(results)}

    def resource_occupation(self, *, uri: str, language: str) -> dict[str, Any]:
        concept_rows = self._query_json(
            "SELECT uri, code, concept_type FROM concepts WHERE uri = ? AND concept_type = 'occupation'",
            (uri,),
        )
        if not concept_rows:
            return {}
        title = self._resolve_label(uri=uri, language=language)
        return {
            "uri": uri,
            "code": concept_rows[0].get("code", ""),
            "title": title,
            "label": title,
            "preferredLabel": title,
            "conceptType": "occupation",
            "type": "occupation",
            "version": self.version,
        }

    def resource_skill(self, *, uri: str, language: str) -> dict[str, Any]:
        concept_rows = self._query_json(
            "SELECT uri, code, concept_type FROM concepts WHERE uri = ? AND concept_type = 'skill'",
            (uri,),
        )
        if not concept_rows:
            return {}
        label = self._resolve_label(uri=uri, language=language)
        return {
            "uri": uri,
            "code": concept_rows[0].get("code", ""),
            "title": label,
            "label": label,
            "preferredLabel": label,
            "conceptType": "skill",
            "type": "skill",
            "version": self.version,
        }

    def resource_related(self, *, uri: str, relation: str, language: str) -> dict[str, Any]:
        rows = self._query_json(
            """
            SELECT r.target_uri as uri, l.label, c.concept_type as conceptType
            FROM relations r
            LEFT JOIN labels l ON r.target_uri = l.uri AND l.language = ?
            LEFT JOIN concepts c ON r.target_uri = c.uri
            WHERE r.source_uri = ? AND r.relation = ?
            ORDER BY l.label
            """,
            (language, uri, relation),
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            related_uri = str(row.get("uri") or "").strip()
            label = str(row.get("label") or "").strip()
            if not label and related_uri:
                label = self._resolve_label(uri=related_uri, language=language)
            concept_type = str(row.get("conceptType") or "skill").strip().lower() or "skill"
            results.append(
                {
                    "uri": related_uri,
                    "title": label,
                    "label": label,
                    "preferredLabel": label,
                    "conceptType": concept_type,
                    "type": concept_type,
                }
            )
        return {"_embedded": {"results": results}, "total": len(results)}


def read_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))
