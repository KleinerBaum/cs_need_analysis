from __future__ import annotations

import wizard_pages.jobad_intake as jobad_intake


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "bestehender upload-text"
        }


def test_extract_upload_to_state_does_not_overwrite_with_empty_text(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    set_error_messages: list[str] = []

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake,
        "extract_text_from_uploaded_file",
        lambda _upload: ("", {"name": "empty.txt", "size": 0}),
    )
    monkeypatch.setattr(
        jobad_intake, "set_error", lambda msg: set_error_messages.append(msg)
    )

    result = jobad_intake._extract_upload_to_state(
        object(), step="test.extract_upload_to_state"
    )

    assert result is None
    assert set_error_messages == ["Datei enthält keinen auslesbaren Inhalt."]
    assert (
        fake_st.session_state[jobad_intake.SOURCE_UPLOAD_TEXT_KEY]
        == "bestehender upload-text"
    )
