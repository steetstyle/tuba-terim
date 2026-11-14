"""TÜBA Türkçe Bilim Terimleri Sözlüğü MCP sunucusu."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Annotated, Any, TypeVar, cast

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .client import TubaClient, TubaError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def _tool(server: MCPServer) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except TubaError as exc:
                raise ToolError(str(exc)) from exc

        return cast(F, server.tool()(wrapper))

    return decorator


def create_server(client: TubaClient | None = None) -> MCPServer:
    tuba = client or TubaClient()
    mcp = MCPServer(
        "tuba-terim",
        instructions=(
            "TÜBA Türkçe Bilim Terimleri Sözlüğü (tubaterim.gov.tr / terim.tuba.gov.tr). "
            "search_tuba maddeyi yeniden açar. Madde başlığı yalnız `entries[].sozcuk` alanıdır ve "
            "`is_heading` true ise sorgu o başlıktır. `other_headings` ve `matched_entries` bu sorgunun "
            "başlığı değildir; tanım için tam başlıkla yeniden sorgula. "
            "TDK Bilim ve Sanat Terimleri ayrı kaynaktır; TÜBA onu değiştirmez. "
            "Yazarken maddeyi bu araçla yeniden aç."
        ),
    )
    tool = _tool(mcp)

    @tool
    async def search_tuba(
        query: Annotated[str, Field(description="Türkçe madde başlığı veya yabancı karşılık.")],
        dictionary: Annotated[
            str | None,
            Field(
                default=None,
                description="İsteğe bağlı: doğa, mühendislik veya sosyal. Boşsa üç sözlük birden aranır.",
            ),
        ] = None,
        match: Annotated[
            str,
            Field(default="exact", description="exact, prefix, suffix veya contains. Varsayılan tam başlık."),
        ] = "exact",
    ) -> dict[str, Any]:
        """TÜBA madde başlığını yeniden aç. Başlık yalnız entries içindeki sozcuk alanıdır."""
        return await tuba.search(query, dictionary, match)

    @tool
    async def list_tuba_dictionaries() -> dict[str, Any]:
        """TÜBA sözlüğündeki üç terim sözlüğünü listele."""
        return await tuba.list_dictionaries()

    return mcp
