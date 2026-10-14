# handlecheck

Check whether a username exists on **YouTube, TikTok, Instagram and Facebook** — without logging in, without API keys, with zero dependencies.

```console
$ handlecheck google zzqxk93jfhw02

== google ==
  tiktok     FOUND      https://www.tiktok.com/@google
  instagram  FOUND      https://www.instagram.com/google/
  facebook   FOUND      https://www.facebook.com/google
  youtube    FOUND      https://www.youtube.com/@google

== zzqxk93jfhw02 ==
  tiktok     NOT FOUND  https://www.tiktok.com/@zzqxk93jfhw02
  instagram  NOT FOUND  https://www.instagram.com/zzqxk93jfhw02/
  facebook   NOT FOUND  https://www.facebook.com/zzqxk93jfhw02
  youtube    NOT FOUND  https://www.youtube.com/@zzqxk93jfhw02
```

## Install

Requires Python 3.9+.

```bash
pip install git+https://github.com/rokib16x/handlecheck.git
```

## Usage

```bash
handlecheck name1 name2                 # one or more usernames
handlecheck -f names.txt                # one per line, '#' comments allowed ('-' = stdin)
handlecheck -p tiktok -p youtube name   # only some platforms
handlecheck name --format json          # or csv / table (default)
handlecheck -f names.txt --delay 3      # wait 3s between usernames (default 1s)
```

As a library:

```python
from handlecheck import check_all, check

for r in check_all("khaby.lame"):
    print(r.platform, r.status.value, r.url)

check("youtube", "google").status   # Status.FOUND
```

Statuses: `FOUND`, `NOT FOUND`, `UNKNOWN` (the check couldn't tell — network error, rate limit, or the site changed), `INVALID` (username contains characters other than letters, digits, `.` and `_`). A leading `@` is ignored.

## How it works

All checks are public, unauthenticated requests:

| Platform  | Method |
|-----------|--------|
| YouTube   | HTTP 404 vs 200 on `/@name` |
| TikTok    | Loads the profile with a mobile user agent; the embedded JSON has `statusCode` `10221` for missing accounts, `0` for existing ones |
| Instagram | Loads the profile as a link-preview crawler (Twitterbot); real profiles have `(@name)` in the page title, missing ones get a bare "Instagram" title |
| Facebook  | Public Graph API `GET /{name}/picture`: 200 if the object exists, 400 if not |

## Limitations — please read

- **These rely on undocumented behaviour.** Sites change, and checks can break or be rate-limited without notice. When that happens you get `UNKNOWN`, not a wrong answer. If one breaks, please open an issue.
- **Facebook** only reliably sees public Pages and vanity URLs. A personal profile with strict privacy settings can show `NOT FOUND` while existing.
- Platforms may throttle or block your IP if you run large batches. Keep `--delay` reasonable.
- Existence of a profile name is not proof of identity. Respect each platform's terms of service and applicable law; use this for things like checking handle availability or verifying your own accounts.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest            # offline unit tests
pytest -m live    # hit the real sites (may be flaky by nature)
ruff check .
```

## License

MIT
