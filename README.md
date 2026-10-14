# handlecheck

Check whether a username exists on **YouTube, TikTok, Instagram, Facebook, X, GitHub and Reddit** — without logging in, without API keys. Use it as a **CLI**, a **Python library**, an **MCP server** (Claude Desktop, Claude Code, Cursor, …), an **HTTP API**, or a **Docker image**. The core has zero dependencies.

```console
$ handlecheck torvalds zzqxk93jfhw02

== torvalds ==
  youtube    NOT FOUND  https://www.youtube.com/@torvalds
  tiktok     FOUND      https://www.tiktok.com/@torvalds
  instagram  FOUND      https://www.instagram.com/torvalds/
  facebook   NOT FOUND  https://www.facebook.com/torvalds
  x          FOUND      https://x.com/torvalds
  github     FOUND      https://github.com/torvalds
  reddit     FOUND      https://www.reddit.com/user/torvalds/

== zzqxk93jfhw02 ==
  youtube    NOT FOUND  https://www.youtube.com/@zzqxk93jfhw02
  ...        NOT FOUND  (all platforms)
```

## Install

```bash
pip install git+https://github.com/rokib16x/handlecheck.git           # CLI + library (Python 3.9+)
pip install "handlecheck[mcp] @ git+https://github.com/rokib16x/handlecheck.git"   # + MCP server (Python 3.10+)
```

## Ways to use it

### 1. CLI

```bash
handlecheck name1 name2                 # one or more usernames
handlecheck -f names.txt                # one per line, '#' comments allowed ('-' = stdin)
handlecheck -p github -p x name         # only some platforms
handlecheck name --format json          # or csv / table (default)
handlecheck -f names.txt --delay 3      # wait 3s between usernames (default 1s)
```

### 2. MCP server (for AI assistants)

Exposes three tools: `check_username`, `check_usernames` (up to 20), `list_platforms`.

**Claude Code**

```bash
claude mcp add handlecheck -- handlecheck-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "handlecheck": { "command": "handlecheck-mcp" }
  }
}
```

If you installed into a virtualenv, use the full path to its `handlecheck-mcp`, or run it without installing via `uvx --from "handlecheck[mcp] @ git+https://github.com/rokib16x/handlecheck.git" handlecheck-mcp`.

Then just ask: *"Is the username `cool.dev` free on GitHub, X and Reddit?"*

### 3. Python library

```python
from handlecheck import check_all, check

for r in check_all("khaby.lame"):
    print(r.platform, r.status.value, r.url)

check("github", "torvalds").status   # Status.FOUND
```

### 4. HTTP API

```bash
handlecheck-api --port 8000            # binds to 127.0.0.1 by default
curl "http://127.0.0.1:8000/check?username=torvalds&platform=github&platform=x"
curl  http://127.0.0.1:8000/platforms
```

There is no authentication — keep it on localhost or put it behind your own gateway.

### 5. Docker

```bash
docker build -t handlecheck .
docker run --rm handlecheck handlecheck torvalds     # CLI
docker run --rm -p 8000:8000 handlecheck             # HTTP API
docker run --rm -i handlecheck handlecheck-mcp       # MCP over stdio
```

## Statuses

`FOUND`, `NOT FOUND`, `UNKNOWN` (couldn't tell: network error, rate limit, or the site changed), `INVALID` (the name can't exist on that platform, e.g. a dot on X — no request is sent). A leading `@` is ignored. Allowed characters overall: letters, digits, `.`, `_`, `-`.

## How it works

All checks are public, unauthenticated requests:

| Platform  | Method |
|-----------|--------|
| YouTube   | HTTP 404 vs 200 on `/@name` |
| TikTok    | Mobile user agent; embedded JSON has `statusCode` `10221` for missing accounts, `0` for existing ones (one retry on bot challenge) |
| Instagram | Link-preview crawler user agent; real profiles have `(@name)` in the page title, missing ones get a bare "Instagram" title |
| Facebook  | Public Graph API `GET /{name}/picture`: 200 if the object exists, 400 if not |
| X         | Crawler user agent on `x.com/name`: 200 vs 404 |
| GitHub    | HTTP 404 vs 200 on `github.com/name` |
| Reddit    | Crawler user agent; real profiles have `(u/name)` in the title, missing ones get the generic Reddit title |

Adding a platform is one decorated function in [`checkers.py`](src/handlecheck/checkers.py) — see `@platform(...)`.

## Limitations — please read

- **These rely on undocumented behaviour.** Sites change and checks can break or be rate-limited without notice. You then get `UNKNOWN`, not a wrong answer. A weekly CI job runs the live tests so breakage shows up; please open an issue if one breaks.
- **Facebook** only reliably sees public Pages and vanity URLs. A personal profile with strict privacy settings can show `NOT FOUND` while existing.
- **X** may return 200 for suspended or protected accounts; that counts as "exists".
- Platforms may throttle or block your IP on large batches. Keep `--delay` reasonable.
- Existence of a profile name is not proof of identity. Respect each platform's terms of service and applicable law; use this for things like checking handle availability or verifying your own accounts.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,mcp]'
pytest            # offline unit tests (includes a real MCP stdio round-trip)
pytest -m live    # hit the real sites (flaky by nature)
ruff check .
```

## License

MIT
