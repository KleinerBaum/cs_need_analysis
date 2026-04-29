# scripts/prepare_esco_for_vectorstore.py

from pathlib import Path
import pandas as pd
import argparse
import re


def clean_text(value) -> str:
    """Normalize missing values and whitespace."""
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_column(columns, candidates):
    """Find the first matching column from a list of possible ESCO column names."""
    normalized = {c.lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def csv_to_markdown(input_csv: Path, output_md: Path, max_rows: int | None = None) -> None:
    df = pd.read_csv(input_csv)

    if max_rows:
        df = df.head(max_rows)

    columns = list(df.columns)

    preferred_label = detect_column(columns, [
        "preferredLabel",
        "preferredLabel/de",
        "preferredLabel/en",
        "preferredLabel_de",
        "preferredLabel_en",
        "title",
        "label",
    ])

    description = detect_column(columns, [
        "description",
        "description/de",
        "description/en",
        "description_de",
        "description_en",
        "scopeNote",
        "definition",
    ])

    uri = detect_column(columns, [
        "conceptUri",
        "conceptType",
        "uri",
        "URI",
        "id",
    ])

    alt_labels = detect_column(columns, [
        "altLabels",
        "altLabels/de",
        "altLabels/en",
        "altLabels_de",
        "altLabels_en",
    ])

    lines = []
    lines.append(f"# ESCO export from {input_csv.name}")
    lines.append("")
    lines.append("This file was normalized from ESCO CSV data for OpenAI File Search / Vector Store retrieval.")
    lines.append("")

    for index, row in df.iterrows():
        title = clean_text(row[preferred_label]) if preferred_label else f"Record {index + 1}"

        lines.append(f"## {title}")
        lines.append("")

        if uri:
            lines.append(f"**URI/ID:** {clean_text(row[uri])}")
            lines.append("")

        if description:
            desc = clean_text(row[description])
            if desc:
                lines.append(f"**Description:** {desc}")
                lines.append("")

        if alt_labels:
            labels = clean_text(row[alt_labels])
            if labels:
                lines.append(f"**Alternative labels:** {labels}")
                lines.append("")

        # Include remaining useful columns without duplicating the main fields.
        skip_cols = {c for c in [preferred_label, description, uri, alt_labels] if c}
        extra_parts = []

        for col in columns:
            if col in skip_cols:
                continue

            value = clean_text(row[col])
            if value:
                extra_parts.append(f"- **{col}:** {value}")

        if extra_parts:
            lines.append("**Additional metadata:**")
            lines.extend(extra_parts)
            lines.append("")

        lines.append("---")
        lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Created: {output_md}")
    print(f"Rows processed: {len(df)}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert ESCO CSV export to Markdown optimized for OpenAI Vector Stores."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_md", type=Path)
    parser.add_argument("--max-rows", type=int, default=None)

    args = parser.parse_args()
    csv_to_markdown(args.input_csv, args.output_md, args.max_rows)


if __name__ == "__main__":
    main()