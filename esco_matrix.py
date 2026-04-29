from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EscoMatrixMetadata:
    source: str
    version: str
    loaded: bool
    records: int


@dataclass(frozen=True)
class EscoMatrixLookup:
    by_occupation_uri: dict[str, dict[str, list[dict[str, Any]]]]
    by_occupation_group: dict[str, dict[str, list[dict[str, Any]]]]
    metadata: EscoMatrixMetadata

    def candidates_for(
        self,
        *,
        occupation_uri: str,
        occupation_group: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        must: list[dict[str, Any]] = []
        nice: list[dict[str, Any]] = []
        if occupation_uri and occupation_uri in self.by_occupation_uri:
            bucket = self.by_occupation_uri[occupation_uri]
            must.extend(bucket.get("must", []))
            nice.extend(bucket.get("nice", []))
        group_key = (occupation_group or "").strip().casefold()
        if group_key and group_key in self.by_occupation_group:
            bucket = self.by_occupation_group[group_key]
            must.extend(bucket.get("must", []))
            nice.extend(bucket.get("nice", []))
        return must, nice


def _normalize_bucket(value: str) -> str:
    bucket = value.strip().casefold()
    if bucket in {"must", "essential", "hasessentialskill"}:
        return "must"
    if bucket in {"nice", "optional", "hasoptionalskill"}:
        return "nice"
    raise ValueError(f"Unsupported matrix bucket '{value}'. Expected must/essential or nice/optional.")


def _append_record(
    target: dict[str, dict[str, list[dict[str, Any]]]],
    *,
    key: str,
    bucket: str,
    skill_uri: str,
    title: str,
) -> None:
    key = key.strip()
    if not key:
        return
    target.setdefault(key, {"must": [], "nice": []})[bucket].append(
        {
            "uri": skill_uri,
            "title": title or skill_uri,
            "type": "skill",
            "source": "ESCO matrix prior",
            "matrix_bucket": bucket,
        }
    )


def load_esco_matrix(path: str | Path) -> EscoMatrixLookup:
    matrix_path = Path(path)
    if not matrix_path.exists():
        raise FileNotFoundError(f"ESCO matrix file not found: {matrix_path}")

    suffix = matrix_path.suffix.lower()
    rows: list[dict[str, Any]]
    metadata_source = str(matrix_path)
    metadata_version = "unknown"

    if suffix == ".json":
        payload = json.loads(matrix_path.read_text(encoding="utf-8"))
        rows = payload.get("records", []) if isinstance(payload, dict) else []
        if isinstance(payload, dict):
            metadata_source = str(payload.get("source") or metadata_source)
            metadata_version = str(payload.get("version") or metadata_version)
    elif suffix == ".csv":
        with matrix_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        raise ValueError("ESCO matrix must be .csv or .json")

    by_uri: dict[str, dict[str, list[dict[str, Any]]]] = {}
    by_group: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        occupation_uri = str(row.get("occupation_uri") or "").strip()
        occupation_group = str(row.get("occupation_group") or "").strip().casefold()
        skill_uri = str(row.get("skill_uri") or "").strip()
        title = str(row.get("skill_title") or row.get("title") or "").strip()
        bucket = _normalize_bucket(str(row.get("bucket") or row.get("relation") or ""))
        if not skill_uri:
            raise ValueError("Matrix record missing required field 'skill_uri'.")
        if not occupation_uri and not occupation_group:
            raise ValueError("Matrix record requires occupation_uri or occupation_group.")
        if occupation_uri:
            _append_record(by_uri, key=occupation_uri, bucket=bucket, skill_uri=skill_uri, title=title)
        if occupation_group:
            _append_record(by_group, key=occupation_group, bucket=bucket, skill_uri=skill_uri, title=title)

    return EscoMatrixLookup(
        by_occupation_uri=by_uri,
        by_occupation_group=by_group,
        metadata=EscoMatrixMetadata(
            source=metadata_source,
            version=metadata_version,
            loaded=True,
            records=len(rows),
        ),
    )
