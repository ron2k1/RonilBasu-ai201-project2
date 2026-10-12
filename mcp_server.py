"""
FitFindr's MCP server. It offers one tool: `search_listings`.

    python mcp_server.py        starts the server (it waits on stdio, that's right)
    python mcp_client.py        asks the server what it offers

`agent.py::run_agent` calls this tool through `mcp_client.call_tool`, so the
search step crosses a process boundary. The two model-calling tools,
`suggest_outfit` and `create_fit_card`, are still direct Python calls.

The registered name is the *function* name, which is why the real
implementation is imported under an alias: without it the registered function
would call itself. FastMCP builds the input schema from the type hints, and the
`Field` descriptions travel with that schema to any client that lists the tool.
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from tools import search_listings as _search_listings_impl

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


@mcp.tool()
def search_listings(
    description: Annotated[str, Field(
        description="Keywords for the item, e.g. 'vintage graphic tee'. Every "
        "meaningful word must appear in the listing; filler such as "
        "'looking for' is ignored. Do not put the size or price in here.",
    )],
    size: Annotated[str | None, Field(
        description="Optional size label, e.g. 'M', 'XL', 'US 8', 'W30 L30' or "
        "'One Size'. Matched as whole tokens: 'M' matches 'S/M' and 'M/L', "
        "'L' does not match 'XL', '8' does not match 'US 8.5'.",
    )] = None,
    max_price: Annotated[float | None, Field(
        description="Optional inclusive price ceiling in US dollars, applied "
        "to the listed price only (shipping is not known). Must be finite "
        "and not negative.",
    )] = None,
) -> list[dict]:
    """Search 40 bundled secondhand clothing listings (sample Depop, thredUp
    and Poshmark data, not live inventory) by keywords, size and price.

    Returns up to 10 complete listings, best keyword match first, then lower
    price. Each listing has id, title, description, category, style_tags
    (list of str), size, condition, price (float, US dollars), colors (list of
    str), brand (str or null) and platform. When nothing matches, it returns
    an empty list. That is a normal answer, not an error: broaden the
    keywords, drop the size, or raise max_price. A negative or non-finite
    max_price is rejected as an error.
    """
    return _search_listings_impl(description, size, max_price)


if __name__ == "__main__":
    mcp.run()
