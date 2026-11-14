# tuba-terim

MCP server for the [TÜBA Turkish Scientific Terminology Dictionary](https://terim.tuba.gov.tr) (also framed by `tubaterim.gov.tr`). It opens live search pages, parses exact headwords from the primary result block, and keeps related hits separate.

## Features

- Exact / prefix / suffix / contains matching across Nature, Engineering, and Social Sciences dictionaries
- Headword field is only `entries[].sozcuk`; related titles never become the query heading
- Disk cache under `~/.cache/tuba-terim-mcp/searches/`
- Uses the macOS system trust store for TLS (`truststore`)

## Install

```bash
uv sync --python 3.13
```

Or with pip:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Cursor config

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tuba-terim": {
      "command": "/ABS/PATH/TO/tuba-terim/.venv/bin/python",
      "args": ["-m", "tuba_terim_mcp", "--transport", "stdio"],
      "cwd": "/ABS/PATH/TO/tuba-terim"
    }
  }
}
```

## Tools

| Tool | Purpose |
|------|---------|
| `search_tuba` | Re-open a TÜBA headword. Optional `dictionary`: `doğa`, `mühendislik`, `sosyal`. Optional `match`: `exact` (default), `prefix`, `suffix`, `contains`. |
| `list_tuba_dictionaries` | List the three TÜBA dictionaries |

## Example

```text
search_tuba(query="kuvvet")
→ is_heading=true, Nature / Engineering / Social entries, English: force

search_tuba(query="özbağlanımlı")
→ is_heading=false; related titles may appear under other_headings
```

## Cache

Successful lookups are cached for 7 days at:

```text
~/.cache/tuba-terim-mcp/searches/
```

Cached responses include `"cache": "hit"`.

## Development

```bash
uv sync --extra dev
.venv/bin/python -m pytest
.venv/bin/python -m tuba_terim_mcp --transport stdio
```

## License

MIT
