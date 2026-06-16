from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from constants import FactResolutionStatus, FactSourceType, SSKey
from schemas import JobAdExtract, JobAdFieldEvidence
import ui_components
import wizard_pages.jobad_intake as jobad_intake


class _DummyColumn:
    def __enter__(self) -> "_DummyColumn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeStreamlit:
    def __init__(
        self,
        *,
        session_state: dict[str, object],
        button_returns: dict[str, bool] | None = None,
    ) -> None:
        self.session_state = session_state
        self._button_returns = button_returns or {}
        self.button_disabled: dict[str, bool] = {}
        self.captions: list[str] = []
        self.successes: list[str] = []
        self.expanders: list[str] = []
        self.rerun_called = False
        self.writes: list[str] = []
        self.markdowns: list[str] = []
        self.tables: list[object] = []
        self.dataframes: list[tuple[object, dict[str, object]]] = []
        self.editor_rows_by_key: dict[str, list[dict[str, object]]] = {}
        self.editor_returns_by_key: dict[str, list[dict[str, object]]] = {}
        self.text_areas: dict[str, str] = {}
        self.selectboxes: dict[str, list[str]] = {}
        self.form_submit_returns: dict[str, bool] = {}
        self.tab_labels: list[list[str]] = []
        self.column_config = SimpleNamespace(
            TextColumn=lambda *args, **kwargs: None,
        )

    def markdown(self, *_args, **_kwargs) -> None:
        if _args:
            self.markdowns.append(str(_args[0]))
        return None

    def caption(self, text: str, *_args, **_kwargs) -> None:
        self.captions.append(text)

    def data_editor(self, rows, **_kwargs):
        key = str(_kwargs.get("key") or "")
        if key:
            self.editor_rows_by_key[key] = rows
            if key in self.editor_returns_by_key:
                return self.editor_returns_by_key[key]
        return rows

    def tabs(self, labels):
        self.tab_labels.append(list(labels))
        return tuple(_DummyColumn() for _label in labels)

    def text_area(self, label: str, *, value: str, key: str, **_kwargs) -> str:
        self.text_areas[key] = label
        return value

    def selectbox(self, label: str, *, options, key: str, **_kwargs) -> str:
        del label
        self.selectboxes[key] = list(options)
        return str(list(options)[0])

    def form(self, _key: str):
        return _DummyColumn()

    def form_submit_button(self, label: str, **_kwargs) -> bool:
        return self.form_submit_returns.get(label, False)

    def columns(self, spec, **_kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            count = len(spec)
        return tuple(_DummyColumn() for _ in range(count))

    def write(self, *_args, **_kwargs) -> None:
        if _args:
            self.writes.append(str(_args[0]))
        return None

    def table(self, *args, **_kwargs) -> None:
        if args:
            self.tables.append(args[0])
        return None

    def dataframe(self, *args, **_kwargs) -> None:
        if args:
            self.dataframes.append((args[0], dict(_kwargs)))
        return None

    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def success(self, text: str, *_args, **_kwargs) -> None:
        self.successes.append(text)

    def expander(self, label: str, expanded: bool = False):
        self.expanders.append(label)
        return _DummyColumn()

    def button(self, _label: str, *, key: str, disabled: bool = False) -> bool:
        self.button_disabled[key] = disabled
        if disabled:
            return False
        return self._button_returns.get(key, False)

    def rerun(self) -> None:
        self.rerun_called = True


def _minimal_identified_info_state() -> dict[str, object]:
    return {
        SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "",
    }


def test_identified_info_next_is_enabled_without_esco_anchor(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state=_minimal_identified_info_state())
    next_calls = {"count": 0}
    ctx = cast(
        jobad_intake.WizardContext,
        SimpleNamespace(
            prev=lambda: None,
            next=lambda: next_calls.__setitem__("count", next_calls["count"] + 1),
        ),
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(
        ui_components, "_render_editable_job_extract", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(jobad_intake, "get_esco_occupation_selected", lambda: None)
    monkeypatch.setattr(jobad_intake, "has_confirmed_esco_anchor", lambda: False)
    overview_calls: list[dict[str, object]] = []

    def _capture_overview(*_args, **kwargs) -> None:
        overview_calls.append(kwargs)

    monkeypatch.setattr(jobad_intake, "render_job_extract_overview", _capture_overview)

    jobad_intake._render_identified_information_block(ctx)

    assert "Analyse abgeschlossen" not in fake_st.successes
    assert (
        "Die wichtigsten Angaben sind vorbereitet. Prüfen Sie kurz die Basisdaten "
        "und bestätigen Sie anschließend den passenden ESCO-Beruf."
        in fake_st.captions
    )
    assert "Technische Details zur Analyse" not in fake_st.expanders
    assert "cs.jobspec.ident_info.next" not in fake_st.button_disabled
    assert (
        "Optional: In Phase C können Sie einen semantischen ESCO-Anker bestätigen."
        in fake_st.captions
    )
    assert overview_calls
    assert overview_calls[0].get("mode") == "compact"
    assert overview_calls[0].get("show_notes") is False
    assert next_calls["count"] == 0
    assert fake_st.rerun_called is False


def test_identified_info_next_uses_selected_occupation_fallback(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state=_minimal_identified_info_state(),
        button_returns={},
    )
    next_calls = {"count": 0}
    ctx = cast(
        jobad_intake.WizardContext,
        SimpleNamespace(
            prev=lambda: None,
            next=lambda: next_calls.__setitem__("count", next_calls["count"] + 1),
        ),
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(
        ui_components, "_render_editable_job_extract", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        jobad_intake,
        "get_esco_occupation_selected",
        lambda: {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Scientist",
            "type": "occupation",
        },
    )
    monkeypatch.setattr(jobad_intake, "has_confirmed_esco_anchor", lambda: True)

    jobad_intake._render_identified_information_block(ctx)

    assert "cs.jobspec.ident_info.next" not in fake_st.button_disabled
    assert "ESCO-Anker bestätigt: Data Scientist" in fake_st.successes
    assert next_calls["count"] == 0
    assert fake_st.rerun_called is False


def test_has_completed_landing_analysis_requires_both_dicts(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
            SSKey.QUESTION_PLAN.value: None,
        }
    )
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    assert jobad_intake._has_completed_landing_analysis() is False


def test_has_completed_landing_analysis_true_when_both_dicts(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state=_minimal_identified_info_state())
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    assert jobad_intake._has_completed_landing_analysis() is True


def test_job_extract_overview_maps_gap_labels_to_german(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(
        ui_components, "_render_editable_job_extract", lambda *_args, **_kwargs: None
    )

    extract = JobAdExtract.model_validate(
        {
            "job_title": "Data Engineer",
            "gaps": ["company_website", "employment_type", "steps", "QuestionPlan"],
            "assumptions": [],
        }
    )

    ui_components.render_job_extract_overview(extract, mode="compact")

    assert not fake_st.tables
    assert fake_st.dataframes
    table_rows, dataframe_kwargs = fake_st.dataframes[0]
    assert dataframe_kwargs["hide_index"] is True
    assert dataframe_kwargs["width"] == "stretch"
    assert {"Attribut": "Location City", "Wert": "—"} in table_rows
    assert {"Attribut": "Start Date", "Wert": "—"} in table_rows
    assert {"Attribut": "Salary Range", "Wert": "—"} in table_rows
    assert {"Attribut": "Recruitment Steps", "Wert": "—"} in table_rows
    assert all("Feld" not in row for row in table_rows)


def test_job_extract_overview_shows_redacted_field_evidence(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(
        ui_components, "_render_editable_job_extract", lambda *_args, **_kwargs: None
    )

    extract = JobAdExtract(
        job_title="Data Engineer",
        field_evidence=[
            JobAdFieldEvidence(
                field_name="job_title",
                confidence=0.82,
                evidence_snippet=(
                    "Kontakt recruiting@example.com sucht Data Engineer."
                ),
                needs_confirmation=True,
            )
        ],
    )

    ui_components.render_job_extract_overview(extract, mode="compact")

    table_rows, _dataframe_kwargs = fake_st.dataframes[0]
    role_row = next(row for row in table_rows if row["Attribut"] == "Rolle")
    assert role_row["Confidence"] == "82% · prüfen"
    assert "recruiting@example.com" not in role_row["Evidence"]
    assert "[REDACTED]" in role_row["Evidence"]
    assert "Data Engineer" in role_row["Evidence"]


def test_editable_job_extract_renders_empty_job_title_for_review(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components._render_editable_job_extract(
        JobAdExtract(company_name="Acme"),
        show_notes=False,
    )

    core_rows = fake_st.editor_rows_by_key["cs.job_extract.core"]
    assert {
        "field": "job_title",
        "label": "Jobtitel",
        "value": "",
    } in core_rows


def test_editable_job_extract_includes_field_evidence_columns(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components._render_editable_job_extract(
        JobAdExtract(
            job_title="Data Engineer",
            field_evidence=[
                JobAdFieldEvidence(
                    field_name="job_title",
                    confidence=0.82,
                    evidence_snippet="Senior Data Engineer im Plattform-Team gesucht.",
                    needs_confirmation=True,
                )
            ],
        ),
        show_notes=False,
    )

    core_rows = fake_st.editor_rows_by_key["cs.job_extract.core"]
    role_row = next(row for row in core_rows if row["field"] == "job_title")
    assert role_row["confidence"] == "82% · prüfen"
    assert role_row["evidence"] == "Senior Data Engineer im Plattform-Team gesucht."


def test_phase_b_hypothesis_form_groups_and_batches_submit(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    fake_st.form_submit_returns["Hypothesen übernehmen"] = True
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    job = JobAdExtract(
        job_title="Data Engineer",
        location_city="Berlin",
        field_evidence=[
            JobAdFieldEvidence(
                field_name="job_title",
                confidence=0.92,
                evidence_snippet="Data Engineer gesucht.",
            ),
            JobAdFieldEvidence(
                field_name="location_city",
                confidence=0.61,
                evidence_snippet="Standort Berlin oder remote.",
                needs_confirmation=True,
            ),
        ],
    )

    jobad_intake._render_job_extract_hypothesis_form(job)

    assert fake_st.tab_labels == [["Basis", "Standort"]]
    assert "cs.jobspec.hypothesis.Basis.editor" in fake_st.editor_rows_by_key
    assert "cs.jobspec.hypothesis.Standort.editor" in fake_st.editor_rows_by_key
    assert fake_st.selectboxes == {}
    assert fake_st.rerun_called is True
    assert fake_st.session_state[SSKey.JOB_EXTRACT.value]["job_title"] == "Data Engineer"
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence["role.job_title"]["source_type"] == FactSourceType.JOBSPEC.value
    assert evidence["role.job_title"]["resolution_status"] == (
        FactResolutionStatus.INFERRED.value
    )


def test_phase_b_hypothesis_form_saves_table_edits_and_deleted_rows(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    fake_st.form_submit_returns["Hypothesen übernehmen"] = True
    fake_st.editor_returns_by_key["cs.jobspec.hypothesis.Basis.editor"] = [
        {
            "field_name": "company_name",
            "Feld": "Unternehmen",
            "Wert": "New GmbH",
            "Status": "Kurz bestätigen",
            "Confidence": "70%",
            "Evidence": "Old GmbH",
        }
    ]
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    job = JobAdExtract(
        job_title="Old Title",
        company_name="Old GmbH",
        field_evidence=[
            JobAdFieldEvidence(
                field_name="job_title",
                confidence=0.9,
                evidence_snippet="Old Title",
            ),
            JobAdFieldEvidence(
                field_name="company_name",
                confidence=0.7,
                evidence_snippet="Old GmbH",
                needs_confirmation=True,
            ),
        ],
    )

    jobad_intake._render_job_extract_hypothesis_form(job)

    reviewed = fake_st.session_state[SSKey.JOB_EXTRACT.value]
    assert reviewed["company_name"] == "New GmbH"
    assert reviewed["job_title"] is None
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence["company.company_name"]["confirmed"] is True
    assert evidence["company.company_name"]["resolution_status"] == (
        FactResolutionStatus.CONFIRMED.value
    )


def test_apply_job_extract_hypothesis_updates_supports_edit_and_skip(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    reviewed = jobad_intake._apply_job_extract_hypothesis_updates(
        JobAdExtract(job_title="Old Title", company_name="Old GmbH"),
        [
            {
                "field_name": "company_name",
                "action": jobad_intake.HYPOTHESIS_ACTION_EDIT,
                "edited_value": "New GmbH",
                "confidence": 0.7,
                "evidence_snippet": "Old GmbH",
            },
            {
                "field_name": "job_title",
                "action": jobad_intake.HYPOTHESIS_ACTION_SKIP,
                "confidence": 0.9,
                "evidence_snippet": "Old Title",
            },
        ],
    )

    assert reviewed.company_name == "New GmbH"
    assert reviewed.job_title is None
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence["company.company_name"]["confirmed"] is True
    assert evidence["company.company_name"]["resolution_status"] == (
        FactResolutionStatus.CONFIRMED.value
    )
    assert "role.job_title" not in fake_st.session_state[SSKey.INTAKE_FACTS.value]
