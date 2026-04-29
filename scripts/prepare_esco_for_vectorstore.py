# F:\ESCO_dataset\prepare_esco_markdown.py

from pathlib import Path
import argparse
import csv
import re
import pandas as pd


DEFAULT_INPUT_DIR = Path(r"F:\ESCO_dataset")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "vectorstore_md"


def clean_text(value) -> str:
    """
    Normalize missing values, line breaks and excessive whitespace.
    """
    if pd.isna(value):
        return ""

    value = str(value)
    value = value.replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_separator(csv_path: Path) -> str:
    """
    ESCO CSV files may use comma, semicolon or tab depending on export/settings.
    This function detects the delimiter from a sample.
    """
    with csv_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        sample = f.read(4096)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        return dialect.delimiter
    except csv.Error:
        # Common fallback for European CSV exports.
        return ","


def read_csv_safely(csv_path: Path) -> pd.DataFrame:
    """
    Read ESCO CSV robustly.
    """
    sep = detect_separator(csv_path)

    return pd.read_csv(
        csv_path,
        sep=sep,
        dtype=str,
        encoding="utf-8-sig",
        keep_default_na=False,
        na_values=[],
        low_memory=False,
    )


def normalize_column_name(column: str) -> str:
    return (
        column.lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
    )


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    """
    Find a useful column even if naming differs slightly.
    """
    normalized_map = {
        normalize_column_name(col): col
        for col in columns
    }

    for candidate in candidates:
        key = normalize_column_name(candidate)
        if key in normalized_map:
            return normalized_map[key]

    return None


def infer_dataset_type(csv_path: Path) -> str:
    """
    Infer the ESCO dataset type from filename.
    """
    name = csv_path.stem.lower()

    if "occupationSkillRelations".lower() in name:
        return "occupation_skill_relations"
    if "skillSkillRelations".lower() in name:
        return "skill_skill_relations"
    if "broaderRelationsOccPillar".lower() in name:
        return "broader_relations_occupation_pillar"
    if "broaderRelationsSkillPillar".lower() in name:
        return "broader_relations_skill_pillar"
    if "occupations".lower() in name:
        return "occupations"
    if "skills".lower() in name:
        return "skills"
    if "skillgroups".lower() in name:
        return "skill_groups"
    if "iscogroups".lower() in name:
        return "isco_groups"
    if "collection".lower() in name:
        return "collections"
    if "hierarchy".lower() in name:
        return "hierarchy"
    if "dictionary".lower() in name:
        return "dictionary"

    return "generic"


def get_primary_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """
    Map likely ESCO columns to semantic roles.
    """
    columns = list(df.columns)

    return {
        "concept_uri": find_column(columns, [
            "conceptUri",
            "concept URI",
            "uri",
            "URI",
            "id",
        ]),
        "preferred_label": find_column(columns, [
            "preferredLabel",
            "preferred label",
            "preferredLabel/de",
            "preferredLabel_de",
            "label",
            "title",
        ]),
        "alt_labels": find_column(columns, [
            "altLabels",
            "alt labels",
            "altLabels/de",
            "altLabels_de",
        ]),
        "hidden_labels": find_column(columns, [
            "hiddenLabels",
            "hidden labels",
            "hiddenLabels/de",
            "hiddenLabels_de",
        ]),
        "description": find_column(columns, [
            "description",
            "description/de",
            "description_de",
            "definition",
            "scopeNote",
            "scope note",
        ]),
        "broader_uri": find_column(columns, [
            "broaderUri",
            "broader URI",
            "broaderConceptUri",
            "parentUri",
        ]),
        "narrower_uri": find_column(columns, [
            "narrowerUri",
            "narrower URI",
            "childUri",
        ]),
        "occupation_uri": find_column(columns, [
            "occupationUri",
            "occupation URI",
            "occupation",
        ]),
        "skill_uri": find_column(columns, [
            "skillUri",
            "skill URI",
            "skill",
        ]),
        "relation_type": find_column(columns, [
            "relationType",
            "relation type",
            "relationshipType",
            "relationship type",
        ]),
        "skill_type": find_column(columns, [
            "skillType",
            "skill type",
            "reuseLevel",
            "reuse level",
        ]),
        "concept_type": find_column(columns, [
            "conceptType",
            "concept type",
            "type",
        ]),
        "isco_group": find_column(columns, [
            "iscoGroup",
            "ISCO group",
            "iscoCode",
            "ISCO code",
        ]),
    }


def row_value(row: pd.Series, column: str | None) -> str:
    if not column:
        return ""
    return clean_text(row.get(column, ""))


def build_title(row: pd.Series, cols: dict[str, str | None], fallback: str) -> str:
    preferred_label = row_value(row, cols["preferred_label"])
    if preferred_label:
        return preferred_label

    concept_uri = row_value(row, cols["concept_uri"])
    if concept_uri:
        return concept_uri

    occupation_uri = row_value(row, cols["occupation_uri"])
    skill_uri = row_value(row, cols["skill_uri"])
    if occupation_uri and skill_uri:
        return f"{occupation_uri} → {skill_uri}"

    return fallback


def build_markdown_for_row(
    row: pd.Series,
    columns: list[str],
    cols: dict[str, str | None],
    dataset_type: str,
    row_number: int,
) -> str:
    """
    Convert one CSV row into a semantically useful Markdown block.
    """
    title = build_title(row, cols, fallback=f"Record {row_number}")

    lines: list[str] = []
    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"**Dataset type:** {dataset_type}")
    lines.append("")

    concept_uri = row_value(row, cols["concept_uri"])
    if concept_uri:
        lines.append(f"**Concept URI:** {concept_uri}")
        lines.append("")

    concept_type = row_value(row, cols["concept_type"])
    if concept_type:
        lines.append(f"**Concept type:** {concept_type}")
        lines.append("")

    description = row_value(row, cols["description"])
    if description:
        lines.append(f"**Description:** {description}")
        lines.append("")

    alt_labels = row_value(row, cols["alt_labels"])
    if alt_labels:
        lines.append(f"**Alternative labels:** {alt_labels}")
        lines.append("")

    hidden_labels = row_value(row, cols["hidden_labels"])
    if hidden_labels:
        lines.append(f"**Hidden labels:** {hidden_labels}")
        lines.append("")

    occupation_uri = row_value(row, cols["occupation_uri"])
    skill_uri = row_value(row, cols["skill_uri"])
    relation_type = row_value(row, cols["relation_type"])

    if occupation_uri or skill_uri or relation_type:
        lines.append("**Relation:**")
        if occupation_uri:
            lines.append(f"- Occupation URI: {occupation_uri}")
        if skill_uri:
            lines.append(f"- Skill URI: {skill_uri}")
        if relation_type:
            lines.append(f"- Relation type: {relation_type}")
        lines.append("")

    broader_uri = row_value(row, cols["broader_uri"])
    narrower_uri = row_value(row, cols["narrower_uri"])

    if broader_uri or narrower_uri:
        lines.append("**Hierarchy:**")
        if broader_uri:
            lines.append(f"- Broader URI: {broader_uri}")
        if narrower_uri:
            lines.append(f"- Narrower URI: {narrower_uri}")
        lines.append("")

    skill_type = row_value(row, cols["skill_type"])
    if skill_type:
        lines.append(f"**Skill type:** {skill_type}")
        lines.append("")

    isco_group = row_value(row, cols["isco_group"])
    if isco_group:
        lines.append(f"**ISCO group:** {isco_group}")
        lines.append("")

    used_columns = {
        col for col in cols.values()
        if col is not None
    }

    additional_metadata = []

    for column in columns:
        if column in used_columns:
            continue

        value = clean_text(row.get(column, ""))
        if value:
            additional_metadata.append(f"- **{column}:** {value}")

    if additional_metadata:
        lines.append("**Additional metadata:**")
        lines.extend(additional_metadata)
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def csv_to_markdown(csv_path: Path, output_dir: Path, max_rows: int | None = None) -> Path:
    df = read_csv_safely(csv_path)

    if max_rows is not None:
        df = df.head(max_rows)

    dataset_type = infer_dataset_type(csv_path)
    columns = list(df.columns)
    cols = get_primary_columns(df)

    output_path = output_dir / f"{csv_path.stem}.md"

    lines: list[str] = []
    lines.append(f"# ESCO dataset: {csv_path.stem}")
    lines.append("")
    lines.append(f"Source file: `{csv_path.name}`")
    lines.append(f"Dataset type: `{dataset_type}`")
    lines.append(f"Rows: `{len(df)}`")
    lines.append("")
    lines.append(
        "This Markdown file was generated from ESCO CSV data for semantic retrieval "
        "with OpenAI Vector Stores / File Search."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for index, row in df.iterrows():
        lines.append(
            build_markdown_for_row(
                row=row,
                columns=columns,
                cols=cols,
                dataset_type=dataset_type,
                row_number=index + 1,
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path


def convert_directory(
    input_dir: Path,
    output_dir: Path,
    pattern: str,
    max_rows: int | None = None,
) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    csv_files = sorted(input_dir.glob(pattern))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {input_dir} with pattern: {pattern}"
        )

    created_files = []

    for csv_path in csv_files:
        print(f"Processing: {csv_path.name}")
        output_path = csv_to_markdown(
            csv_path=csv_path,
            output_dir=output_dir,
            max_rows=max_rows,
        )
        created_files.append(output_path)
        print(f"Created: {output_path}")

    return created_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert ESCO German CSV files to Markdown optimized for OpenAI Vector Stores."
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=r"Directory containing ESCO CSV files. Default: F:\ESCO_dataset",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=r"Directory for generated Markdown files. Default: F:\ESCO_dataset\vectorstore_md",
    )

    parser.add_argument(
        "--pattern",
        default="*_de.csv",
        help="CSV file pattern to process. Default: *_de.csv",
    )

    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional row limit for testing.",
    )

    args = parser.parse_args()

    created_files = convert_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        pattern=args.pattern,
        max_rows=args.max_rows,
    )

    print("")
    print("Done.")
    print(f"Markdown files created: {len(created_files)}")
    print(f"Output directory: {args.output_dir}")

    for file in created_files:
        print(f"- {file.name}")


if __name__ == "__main__":
    main()