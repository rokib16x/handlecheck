"""Offline tests: HTTP is stubbed, so no network is needed."""
import pytest

from handlecheck import Status, check, checkers, validate_username


def stub(monkeypatch, status, body=""):
    monkeypatch.setattr(checkers.http, "fetch", lambda *a, **k: (status, body))


@pytest.mark.parametrize("name", ["a", "khaby.lame", "the_rock", "__x__", "x" * 64, "@google"])
def test_valid_usernames(name):
    assert validate_username(name) == name.lstrip("@")


@pytest.mark.parametrize("name", ["", "bad name", "../etc/passwd", "a/b", "x" * 65, "a?b=1", "é"])
def test_invalid_usernames(name):
    with pytest.raises(ValueError):
        validate_username(name)


def test_invalid_username_makes_no_request(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(checkers.http, "fetch", boom)
    assert check("youtube", "bad name").status is Status.INVALID


@pytest.mark.parametrize(
    "status,expected",
    [(200, Status.FOUND), (404, Status.NOT_FOUND), (429, Status.UNKNOWN)],
)
def test_youtube(monkeypatch, status, expected):
    stub(monkeypatch, status)
    assert check("youtube", "x").status is expected


@pytest.mark.parametrize(
    "body,expected",
    [
        ('..."statusCode":0...', Status.FOUND),
        ('..."statusCode":10221...', Status.NOT_FOUND),
        ('..."statusCode":999...', Status.UNKNOWN),
        ("<html>challenge</html>", Status.UNKNOWN),
    ],
)
def test_tiktok(monkeypatch, body, expected):
    stub(monkeypatch, 200, body)
    assert check("tiktok", "x").status is expected


def test_tiktok_retries_once(monkeypatch):
    bodies = iter(["challenge", '"statusCode":0'])
    monkeypatch.setattr(checkers.http, "fetch", lambda *a, **k: (200, next(bodies)))
    assert check("tiktok", "x").status is Status.FOUND


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (200, "<title>Google (&#064;Google) • Instagram</title>", Status.FOUND),
        (200, "<title>Instagram</title>", Status.NOT_FOUND),
        (404, "", Status.NOT_FOUND),
        (200, "<title>Somebody else (@other)</title>", Status.UNKNOWN),
        (500, "", Status.UNKNOWN),
    ],
)
def test_instagram(monkeypatch, status, body, expected):
    stub(monkeypatch, status, body)
    assert check("instagram", "google").status is expected


@pytest.mark.parametrize(
    "status,expected", [(200, Status.FOUND), (400, Status.NOT_FOUND), (500, Status.UNKNOWN)]
)
def test_facebook(monkeypatch, status, expected):
    stub(monkeypatch, status)
    assert check("facebook", "x").status is expected


def test_network_error_is_unknown(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError

    monkeypatch.setattr(checkers.http, "fetch", boom)
    r = check("youtube", "x")
    assert r.status is Status.UNKNOWN and r.detail == "TimeoutError"
