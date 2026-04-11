from salary.mapping import infer_occupation_id, infer_region_id, normalize_token
from salary.types import SalaryEscoContext


def test_normalize_token_normalizes_case_accents_and_whitespace() -> None:
    assert normalize_token("  München / Data-Science  ") == "munchen data science"


def test_infer_region_id_maps_de_city_to_bundesland() -> None:
    assert infer_region_id("Deutschland", "Berlin") == "DE-BE"
    assert infer_region_id("DE", "München") == "DE-BY"


def test_infer_region_id_falls_back_to_de_for_unknown_de_city() -> None:
    assert infer_region_id("Germany", "Unbekannt") == "DE"


def test_infer_occupation_id_prefers_esco_uri() -> None:
    context = SalaryEscoContext(
        occupation_uri="http://data.europa.eu/esco/occupation/1234"
    )
    assert (
        infer_occupation_id(context, "Senior Data Scientist")
        == "esco::http://data.europa.eu/esco/occupation/1234"
    )


def test_infer_occupation_id_uses_title_fallback() -> None:
    assert (
        infer_occupation_id(None, " Senior Data Scientist  ")
        == "title::senior data scientist"
    )
    assert infer_occupation_id(None, None) == "title::unknown"
