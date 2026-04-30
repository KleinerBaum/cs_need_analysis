from __future__ import annotations

import esco_rag


def test_infer_source_metadata_known_markdown_filenames() -> None:
    expected = {
        "occupation_profiles_de.md": ("occupations", "de", "unknown"),
        "occupation_profiles_en.md": ("occupations", "en", "unknown"),
        "skills_essential_de.md": ("skills", "de", "essential"),
        "skills_essential_en.md": ("skills", "en", "essential"),
        "skills_optional_de.md": ("skills", "de", "optional"),
        "skills_optional_en.md": ("skills", "en", "optional"),
        "skills_transversal_de.md": ("skills", "de", "transversal"),
        "skills_transversal_en.md": ("skills", "en", "transversal"),
    }

    for filename, metadata in expected.items():
        source_file, collection, language, skill_type = esco_rag._infer_source_metadata(
            filename
        )
        assert source_file == filename
        assert (collection, language, skill_type) == metadata


def test_infer_source_metadata_unknown_fallback() -> None:
    source_file, collection, language, skill_type = esco_rag._infer_source_metadata(
        "custom_esco_chunk.md"
    )

    assert source_file == "custom_esco_chunk.md"
    assert collection == "unknown"
    assert language == "unknown"
    assert skill_type == "unknown"
