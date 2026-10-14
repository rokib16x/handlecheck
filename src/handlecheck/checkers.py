"""Per-platform existence checks. Each checker returns a Status for one username."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib.parse import quote

from . import http

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,64}$")


class Status(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT FOUND"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


@dataclass(frozen=True)
class Result:
    platform: str
    username: str
    status: Status
    url: str
    detail: str = ""


def validate_username(username: str) -> str:
    """Strip a leading '@' and reject anything outside letters, digits, '.' and '_'."""
    name = username.strip().lstrip("@")
    if not USERNAME_RE.match(name):
        raise ValueError(f"invalid username: {username!r}")
    return name


def _youtube(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://www.youtube.com/@{quote(u)}")
    if status == 200:
        return Status.FOUND, ""
    if status == 404:
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


def _tiktok(u: str) -> tuple[Status, str]:
    m = None
    for _ in range(2):  # TikTok occasionally serves a bot challenge; retry once
        status, body = http.fetch(f"https://www.tiktok.com/@{quote(u)}", http.MOBILE_UA)
        m = re.search(r'"statusCode":(\d+)', body)
        if m:
            break
    if not m:
        return Status.UNKNOWN, f"no data, HTTP {status}"
    if m.group(1) == "0":
        return Status.FOUND, ""
    if m.group(1) == "10221":
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"code {m.group(1)}"


def _instagram(u: str) -> tuple[Status, str]:
    status, body = http.fetch(f"https://www.instagram.com/{quote(u)}/", http.CRAWLER_UA)
    if status == 404:
        return Status.NOT_FOUND, ""
    m = re.search(r"<title>([^<]*)</title>", body)
    title = (m.group(1) if m else "").lower()
    if f"(&#064;{u.lower()})" in title or f"(@{u.lower()})" in title:
        return Status.FOUND, ""
    if title.strip() == "instagram":  # generic page served for missing profiles
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


def _facebook(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://graph.facebook.com/{quote(u)}/picture?redirect=false")
    if status == 200:
        return Status.FOUND, ""
    if status == 400:
        return Status.NOT_FOUND, "private profiles may also appear here"
    return Status.UNKNOWN, f"HTTP {status}"


PROFILE_URLS = {
    "tiktok": "https://www.tiktok.com/@{u}",
    "instagram": "https://www.instagram.com/{u}/",
    "facebook": "https://www.facebook.com/{u}",
    "youtube": "https://www.youtube.com/@{u}",
}

CHECKERS: dict[str, Callable[[str], tuple[Status, str]]] = {
    "tiktok": _tiktok,
    "instagram": _instagram,
    "facebook": _facebook,
    "youtube": _youtube,
}


def check(platform: str, username: str) -> Result:
    """Check one username on one platform. Network errors become Status.UNKNOWN."""
    try:
        name = validate_username(username)
    except ValueError as e:
        return Result(platform, username, Status.INVALID, "", str(e))
    url = PROFILE_URLS[platform].format(u=name)
    try:
        status, detail = CHECKERS[platform](name)
    except Exception as e:  # noqa: BLE001 - any failure should degrade to UNKNOWN
        status, detail = Status.UNKNOWN, type(e).__name__
    return Result(platform, name, status, url, detail)


def check_all(username: str, platforms: list[str] | None = None) -> list[Result]:
    """Check one username on several platforms in parallel (default: all)."""
    platforms = platforms or list(CHECKERS)
    with ThreadPoolExecutor(max_workers=len(platforms)) as pool:
        return list(pool.map(lambda p: check(p, username), platforms))
