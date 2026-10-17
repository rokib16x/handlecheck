"""Per-platform existence checks. Each checker returns a Status for one username."""
from __future__ import annotations

import re
import smtplib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib.parse import quote

from . import http

# Superset of what any supported platform allows; keeps usernames safe to put in a URL.
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


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


@dataclass(frozen=True)
class Platform:
    name: str
    url: str  # profile URL template with {u}
    check: Callable[[str], tuple[Status, str]]
    handle_re: re.Pattern  # what the platform itself accepts; anything else cannot exist


PLATFORMS: dict[str, Platform] = {}


def platform(name: str, url: str, handle: str):
    """Register a checker for `name`; `handle` is a regex for names the site allows."""

    def deco(fn: Callable[[str], tuple[Status, str]]):
        PLATFORMS[name] = Platform(name, url, fn, re.compile(handle))
        return fn

    return deco


def validate_username(username: str) -> str:
    """Strip a leading '@' and reject anything outside letters, digits, '.', '_' and '-'."""
    name = username.strip().lstrip("@")
    if not USERNAME_RE.match(name):
        raise ValueError(f"invalid username: {username!r}")
    return name


@platform("youtube", "https://www.youtube.com/@{u}", r"^[A-Za-z0-9._-]{3,30}$")
def _youtube(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://www.youtube.com/@{quote(u)}")
    if status == 200:
        return Status.FOUND, ""
    if status == 404:
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


@platform("tiktok", "https://www.tiktok.com/@{u}", r"^[A-Za-z0-9._]{2,24}$")
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


@platform("instagram", "https://www.instagram.com/{u}/", r"^[A-Za-z0-9._]{1,30}$")
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


@platform("facebook", "https://www.facebook.com/{u}", r"^[A-Za-z0-9.]{5,50}$")
def _facebook(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://graph.facebook.com/{quote(u)}/picture?redirect=false")
    if status == 200:
        return Status.FOUND, ""
    if status == 400:
        return Status.NOT_FOUND, "private profiles may also appear here"
    return Status.UNKNOWN, f"HTTP {status}"


@platform("x", "https://x.com/{u}", r"^[A-Za-z0-9_]{1,15}$")
def _x(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://x.com/{quote(u)}", http.CRAWLER_UA)
    if status == 200:
        return Status.FOUND, ""
    if status == 404:
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


@platform("github", "https://github.com/{u}", r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
def _github(u: str) -> tuple[Status, str]:
    status, _ = http.fetch(f"https://github.com/{quote(u)}")
    if status == 200:
        return Status.FOUND, ""
    if status == 404:
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


@platform("reddit", "https://www.reddit.com/user/{u}/", r"^[A-Za-z0-9_-]{3,20}$")
def _reddit(u: str) -> tuple[Status, str]:
    status, body = http.fetch(f"https://www.reddit.com/user/{quote(u)}/", http.CRAWLER_UA)
    m = re.search(r"<title>([^<]*)</title>", body)
    title = (m.group(1) if m else "").lower()
    if f"(u/{u.lower()})" in title:
        return Status.FOUND, ""
    if "the heart of the internet" in title:  # generic page served for missing users
        return Status.NOT_FOUND, ""
    return Status.UNKNOWN, f"HTTP {status}"


GMAIL_MX = "gmail-smtp-in.l.google.com"


@platform(
    "gmail",
    "mailto:{u}@gmail.com",
    # Gmail: 6-30 letters/digits/dots; no leading, trailing or consecutive dots
    r"^(?!.*\.\.)(?!\.)(?!.*\.$)[A-Za-z0-9.]{6,30}$",
)
def _gmail(u: str) -> tuple[Status, str]:
    """Ask Google's mail server whether `u@gmail.com` would accept mail (SMTP RCPT TO).

    No message is sent and no login is used. Needs outbound port 25, which many home
    ISPs and cloud hosts (including GitHub Actions) block; that yields UNKNOWN.
    FOUND means the address is taken. Gmail ignores dots, so a.b and ab are the same.
    """
    try:
        with smtplib.SMTP(GMAIL_MX, 25, timeout=8) as smtp:
            smtp.ehlo("example.com")
            smtp.mail("check@example.com")
            code, msg = smtp.rcpt(f"{u}@gmail.com")
    except (OSError, smtplib.SMTPException) as e:
        return Status.UNKNOWN, f"SMTP unreachable ({type(e).__name__}); is port 25 blocked?"
    text = msg.decode("utf-8", errors="ignore") if isinstance(msg, bytes) else str(msg)
    if code in (250, 251):
        return Status.FOUND, "address exists (taken)"
    if code == 550 and "5.1.1" in text:
        return Status.NOT_FOUND, "no such Gmail account (likely available)"
    return Status.UNKNOWN, f"SMTP {code}"


# name -> checker, kept for backwards compatibility and easy iteration
CHECKERS = {name: p.check for name, p in PLATFORMS.items()}
PROFILE_URLS = {name: p.url for name, p in PLATFORMS.items()}


def check(platform: str, username: str) -> Result:
    """Check one username on one platform. Network errors become Status.UNKNOWN."""
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform {platform!r}; choose from {sorted(PLATFORMS)}")
    p = PLATFORMS[platform]
    try:
        name = validate_username(username)
    except ValueError as e:
        return Result(platform, username, Status.INVALID, "", str(e))
    url = p.url.format(u=name)
    if not p.handle_re.match(name):
        return Result(platform, name, Status.INVALID, url, f"not a valid {platform} username")
    try:
        status, detail = p.check(name)
    except Exception as e:  # noqa: BLE001 - any failure should degrade to UNKNOWN
        status, detail = Status.UNKNOWN, type(e).__name__
    return Result(platform, name, status, url, detail)


def check_all(username: str, platforms: list[str] | None = None) -> list[Result]:
    """Check one username on several platforms in parallel (default: all)."""
    platforms = platforms or list(PLATFORMS)
    with ThreadPoolExecutor(max_workers=len(platforms)) as pool:
        return list(pool.map(lambda p: check(p, username), platforms))
