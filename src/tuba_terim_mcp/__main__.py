"""CLI: `python -m tuba_terim_mcp`."""

from __future__ import annotations

import argparse
import logging
import sys

from .server import create_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tuba-terim-mcp")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    kwargs: dict[str, object] = {"transport": args.transport}
    if args.transport in {"streamable-http", "sse"}:
        kwargs.update(host=args.host, port=args.port)
    create_server().run(**kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
