"""Minimal HTTP helper (stdlib only)."""
import urllib.error
import urllib.request

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
CRAWLER_UA = "Twitterbot/1.0"


def fetch(url: str, ua: str = DESKTOP_UA, timeout: float = 15) -> tuple[int, str]:
    """GET `url` and return (status, body). HTTP error statuses are returned, not raised."""
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(2_000_000).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
