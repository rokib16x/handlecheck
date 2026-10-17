"""Offline tests: HTTP is stubbed, so no network is needed."""
import pytest

from handlecheck import Status, check, checkers, validate_username


def stub(monkeypatch, status, body=""):
    monkeypatch.setattr(checkers.http, "fetch", lambda *a, **k: (status, body))


@pytest.mark.parametrize("name", ["a", "khaby.lame", "the_rock", "__x__", "x" * 64, "@google", "sp-ez"])
def test_valid_usernames(name):
    assert validate_username(name) == name.lstrip("@")


@pytest.mark.parametrize("name", ["", "bad name", "../etc/passwd", "a/b", "x" * 65, "a?b=1", "é", "a@b"])
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
    assert check("youtube", "someone").status is expected


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
    assert check("tiktok", "someone").status is expected


def test_tiktok_retries_once(monkeypatch):
    bodies = iter(["challenge", '"statusCode":0'])
    monkeypatch.setattr(checkers.http, "fetch", lambda *a, **k: (200, next(bodies)))
    assert check("tiktok", "someone").status is Status.FOUND


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
    assert check("facebook", "someone.real").status is expected


def test_network_error_is_unknown(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError

    monkeypatch.setattr(checkers.http, "fetch", boom)
    r = check("youtube", "someone")
    assert r.status is Status.UNKNOWN and r.detail == "TimeoutError"


@pytest.mark.parametrize(
    "platform,title,expected",
    [
        ("reddit", "spez (u/spez) - Reddit", Status.FOUND),
        ("reddit", "Reddit - The heart of the internet", Status.NOT_FOUND),
        ("reddit", "Just a moment...", Status.UNKNOWN),
    ],
)
def test_reddit(monkeypatch, platform, title, expected):
    stub(monkeypatch, 200, f"<title>{title}</title>")
    assert check(platform, "spez").status is expected


@pytest.mark.parametrize("platform", ["x", "github"])
@pytest.mark.parametrize(
    "status,expected", [(200, Status.FOUND), (404, Status.NOT_FOUND), (429, Status.UNKNOWN)]
)
def test_status_code_platforms(monkeypatch, platform, status, expected):
    stub(monkeypatch, status)
    assert check(platform, "someone").status is expected


@pytest.mark.parametrize(
    "platform,name",
    [
        ("x", "has.dot"),  # X: letters, digits, underscore only
        ("x", "waytoolongusername1"),  # X: max 15
        ("github", "-leading"),  # GitHub: cannot start with a hyphen
        ("github", "under_score"),
        ("reddit", "ab"),  # Reddit: min 3
        ("facebook", "abc"),  # Facebook: min 5
    ],
)
def test_platform_rules_reject_without_network(monkeypatch, platform, name):
    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(checkers.http, "fetch", boom)
    assert check(platform, name).status is Status.INVALID


def test_unknown_platform():
    with pytest.raises(ValueError):
        check("myspace", "someone")


class FakeSMTP:
    reply = (250, b"2.1.5 OK")

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self, *a):
        pass

    def mail(self, *a):
        pass

    def rcpt(self, addr):
        return self.reply


@pytest.mark.parametrize(
    "reply,expected",
    [
        ((250, b"2.1.5 OK"), Status.FOUND),
        ((550, b"5.1.1 The email account that you tried to reach does not exist"), Status.NOT_FOUND),
        ((550, b"5.7.1 blocked"), Status.UNKNOWN),
        ((421, b"4.7.0 try later"), Status.UNKNOWN),
    ],
)
def test_gmail(monkeypatch, reply, expected):
    monkeypatch.setattr(checkers.smtplib, "SMTP", type("S", (FakeSMTP,), {"reply": reply}))
    assert check("gmail", "someone.real").status is expected


def test_gmail_port_blocked_is_unknown(monkeypatch):
    def boom(*a, **k):
        raise OSError("blocked")

    monkeypatch.setattr(checkers.smtplib, "SMTP", boom)
    r = check("gmail", "someone.real")
    assert r.status is Status.UNKNOWN and "port 25" in r.detail


@pytest.mark.parametrize("name", ["short", ".leading1", "trailing1.", "dou..ble1", "has_underscore", "x" * 31])
def test_gmail_rules_reject_without_network(monkeypatch, name):
    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(checkers.smtplib, "SMTP", boom)
    assert check("gmail", name).status is Status.INVALID
