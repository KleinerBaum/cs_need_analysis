from __future__ import annotations

import socket

import pytest

import homepage_research


class _FakeHeaders:
    def __init__(
        self,
        content_type: str = "text/html",
        extra: dict[str, str] | None = None,
    ) -> None:
        self._content_type = content_type
        self._extra = {
            str(key).casefold(): str(value) for key, value in (extra or {}).items()
        }

    def get_content_charset(self) -> str:
        return "utf-8"

    def get_content_type(self) -> str:
        return self._content_type

    def get(self, key: str, default: str = "") -> str:
        if key.casefold() == "content-type":
            return self._content_type
        return self._extra.get(key.casefold(), default)


class _FakeResponse:
    def __init__(
        self,
        payload: str,
        *,
        final_url: str = "https://example.com",
        content_type: str = "text/html",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._payload = payload.encode("utf-8")
        self._final_url = final_url
        self.headers = _FakeHeaders(content_type, headers)
        self.status = status_code
        self.code = status_code
        self.closed = False
        self.read_calls = 0

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return self._final_url

    def getcode(self) -> int:
        return self.status

    def read(self, _size: int = -1) -> bytes:
        self.read_calls += 1
        return self._payload

    def close(self) -> None:
        self.closed = True


def _patch_dns(
    monkeypatch: pytest.MonkeyPatch,
    records: dict[str, tuple[str, ...]] | None = None,
    *,
    call_counter: dict[str, int] | None = None,
) -> None:
    resolved = records or {"example.com": ("93.184.216.34",)}

    def fake_getaddrinfo(
        host: str,
        _port: object,
        *_args: object,
        **_kwargs: object,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        if call_counter is not None:
            call_counter["count"] = call_counter.get("count", 0) + 1
        addresses = resolved.get(str(host).strip("[]").casefold())
        if addresses is None:
            raise OSError("unresolved test host")
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                0,
                "",
                (address, 0),
            )
            for address in addresses
        ]

    monkeypatch.setattr(homepage_research.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture(autouse=True)
def _clear_homepage_fetch_policy_state(monkeypatch: pytest.MonkeyPatch) -> None:
    homepage_research.clear_fetch_cache()
    monkeypatch.delenv(
        homepage_research.HOMEPAGE_FETCH_ALLOWED_DOMAINS_ENV,
        raising=False,
    )


@pytest.mark.parametrize(
    "raw_url",
    [
        "localhost",
        "http://127.0.0.1:8501",
        "https://192.168.0.10",
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://[fe80::1%25eth0]/",
        "https://example.com@127.0.0.1/",
        "https://service.localhost/",
    ],
)
def test_security_contract_blocks_local_or_private_targets_without_network(
    monkeypatch: pytest.MonkeyPatch,
    raw_url: str,
) -> None:
    def fail_if_opened(_request: object, _timeout_sec: float) -> _FakeResponse:
        raise AssertionError("Fetch should not start for disallowed targets")

    monkeypatch.setattr(homepage_research, "_open_url", fail_if_opened)

    assert homepage_research.normalize_url(raw_url) == ""
    with pytest.raises(homepage_research.HomepageFetchError):
        homepage_research.fetch_url_text_result(raw_url)


def test_security_contract_blocks_hostname_resolving_to_private_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dns(monkeypatch, {"example.com": ("10.0.0.5",)})

    def fail_if_opened(_request: object, _timeout_sec: float) -> _FakeResponse:
        raise AssertionError("Fetch should not start for private DNS targets")

    monkeypatch.setattr(homepage_research, "_open_url", fail_if_opened)

    with pytest.raises(homepage_research.HomepageFetchError) as exc_info:
        homepage_research.fetch_url_text_result("https://example.com")

    assert exc_info.value.error_code == "invalid_or_disallowed_url"
    assert exc_info.value.from_negative_cache is False


def test_host_negative_cache_suppresses_repeated_private_dns_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = {"value": 1_000.0}
    dns_calls = {"count": 0}
    monkeypatch.setattr(homepage_research.time, "time", lambda: now["value"])
    _patch_dns(
        monkeypatch,
        {"example.com": ("10.0.0.5",)},
        call_counter=dns_calls,
    )

    with pytest.raises(homepage_research.HomepageFetchError) as first_exc:
        homepage_research.fetch_url_text_result("https://example.com/a")
    assert first_exc.value.from_negative_cache is False
    assert dns_calls["count"] == 1

    with pytest.raises(homepage_research.HomepageFetchError) as second_exc:
        homepage_research.fetch_url_text_result("https://example.com/b")
    assert second_exc.value.from_negative_cache is True
    assert second_exc.value.suppressed_repeat_count == 1
    assert dns_calls["count"] == 1

    now["value"] += homepage_research.HOMEPAGE_FETCH_NEGATIVE_CACHE_TTL_SECONDS + 1
    with pytest.raises(homepage_research.HomepageFetchError) as third_exc:
        homepage_research.fetch_url_text_result("https://example.com/c")
    assert third_exc.value.from_negative_cache is False
    assert dns_calls["count"] == 2


def test_url_negative_cache_suppresses_response_policy_failures_by_exact_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dns(monkeypatch)
    opened_urls: list[str] = []

    def fake_open_url(request: object, _timeout_sec: float) -> _FakeResponse:
        request_url = str(getattr(request, "full_url"))
        opened_urls.append(request_url)
        return _FakeResponse(
            "%PDF-1.7",
            final_url=request_url,
            content_type="application/pdf",
        )

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="unsupported"):
        homepage_research.fetch_url_text_result("https://example.com/policy")

    with pytest.raises(homepage_research.HomepageFetchError) as second_exc:
        homepage_research.fetch_url_text_result("https://example.com/policy")
    assert second_exc.value.from_negative_cache is True
    assert second_exc.value.suppressed_repeat_count == 1

    with pytest.raises(homepage_research.HomepageFetchError, match="unsupported"):
        homepage_research.fetch_url_text_result("https://example.com/other")
    assert opened_urls == ["https://example.com/policy", "https://example.com/other"]


def test_redirect_loop_is_negative_cached_by_initial_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dns(monkeypatch)
    opened_urls: list[str] = []

    def fake_open_url(request: object, _timeout_sec: float) -> _FakeResponse:
        request_url = str(getattr(request, "full_url"))
        opened_urls.append(request_url)
        return _FakeResponse(
            "",
            final_url=request_url,
            status_code=302,
            headers={"Location": f"https://example.com/r{len(opened_urls)}"},
        )

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="too_many"):
        homepage_research.fetch_url_text_result("https://example.com")
    assert len(opened_urls) == homepage_research.HOMEPAGE_FETCH_MAX_REDIRECTS + 1

    with pytest.raises(homepage_research.HomepageFetchError) as second_exc:
        homepage_research.fetch_url_text_result("https://example.com")
    assert second_exc.value.error_code == "too_many_redirects"
    assert second_exc.value.from_negative_cache is True
    assert len(opened_urls) == homepage_research.HOMEPAGE_FETCH_MAX_REDIRECTS + 1


def test_allowlist_accepts_exact_and_subdomains_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        homepage_research.HOMEPAGE_FETCH_ALLOWED_DOMAINS_ENV,
        "example.com",
    )

    assert homepage_research.normalize_url("https://example.com") == "https://example.com"
    assert (
        homepage_research.normalize_url("https://www.example.com/about")
        == "https://www.example.com/about"
    )
    assert homepage_research.normalize_url("https://badexample.com") == ""
    assert homepage_research.normalize_url("https://example.com.evil.test") == ""


def test_allowlist_applies_to_extracted_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        homepage_research.HOMEPAGE_FETCH_ALLOWED_DOMAINS_ENV,
        "example.com",
    )
    raw_html = """
    <a href="/about">About</a>
    <a href="https://badexample.com/about">Bad suffix</a>
    <a href="https://example.com.evil.test/about">Evil suffix</a>
    """

    links = homepage_research.extract_links("https://example.com", raw_html)

    assert links == [("About", "https://example.com/about")]


def test_allowlist_revalidates_redirect_targets_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        homepage_research.HOMEPAGE_FETCH_ALLOWED_DOMAINS_ENV,
        "example.com",
    )
    _patch_dns(
        monkeypatch,
        {
            "example.com": ("93.184.216.34",),
            "evil.test": ("93.184.216.34",),
        },
    )
    redirect_response = _FakeResponse(
        "",
        final_url="https://example.com",
        status_code=302,
        headers={"Location": "https://evil.test/private"},
    )

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        return redirect_response

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="redirect"):
        homepage_research.fetch_url_text_result("https://example.com")
    assert redirect_response.read_calls == 0
    assert redirect_response.closed is True
