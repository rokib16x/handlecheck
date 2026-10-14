import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from handlecheck import Status, api
from handlecheck.checkers import Result


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(
        api, "check_all",
        lambda name, platforms=None: [Result("github", name, Status.FOUND, "u")],
    )
    srv = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_check(server):
    code, data = get(f"{server}/check?username=a&username=b&platform=github")
    assert code == 200 and [d["username"] for d in data] == ["a", "b"]
    assert data[0]["status"] == "FOUND"


def test_platforms(server):
    code, data = get(f"{server}/platforms")
    assert code == 200 and "github" in data


@pytest.mark.parametrize("path", ["/check", "/check?username=a&platform=myspace", "/nope"])
def test_errors(server, path):
    assert get(server + path)[0] in (400, 404)
