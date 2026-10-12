"""FitFindr's planning loop and visible state for one request."""

from copy import deepcopy
import json
import math
import re

import trace
from generate import ModelUnavailable, QuotaGuard
from mcp_client import MCPError, call_tool
from tools import suggest_outfit, create_fit_card


_PRICE = re.compile(
    r"(?:(?:\b(?:under|below|up\s+to|max(?:imum)?(?:\s+price)?|budget(?:\s+of)?))"
    r"\s*\$?\s*|\$\s*)(-?\d+(?:\.\d{1,2})?)(?!\d|[.,]\d)",
    re.IGNORECASE,
)
_SIZE = re.compile(
    r"\bsize\s+(one\s+size|w\d+(?:\s+l\d+)?|(?:us\s*)?\d+(?:\.\d+)?"
    r"|(?:xxxl|xxl|xxs|xs|xl|s|m|l)(?:/(?:xxxl|xxl|xxs|xs|xl|s|m|l))?)"
    r"(?![a-z0-9]|\.\d)",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """Extract optional labeled size and price ceiling without a model call."""
    description = query.strip()
    if not description:
        raise ValueError("Describe an item, such as 'graphic tee under $30, size M'.")
    prices = list(_PRICE.finditer(description))
    if len(prices) > 1:
        raise ValueError("Use one maximum price, such as 'under $30'.")
    max_price = float(prices[0].group(1)) if prices else None
    if max_price is not None and (not math.isfinite(max_price) or max_price < 0):
        raise ValueError("Use a finite, nonnegative budget, such as 'under $30'.")
    description = _PRICE.sub(" ", description)
    if "$" in description or re.search(
        r"\b(?:under|below|up\s+to|max(?:imum)?(?:\s+price)?|budget)\b",
        description, re.IGNORECASE,
    ):
        raise ValueError("Write the budget as a number, such as 'under $30'.")
    sizes = list(_SIZE.finditer(description))
    if len(sizes) > 1:
        raise ValueError("Use one size request, such as 'size M'.")
    size = re.sub(r"\s+", " ", sizes[0].group(1)).upper() if sizes else None
    description = _SIZE.sub(" ", description)
    if re.search(r"\bsize\b", description, re.IGNORECASE):
        raise ValueError("Use a size label such as 'size M', 'size US 8', or 'size W30 L30'.")
    description = re.sub(r"\s+", " ", description.replace(",", " ")).strip()
    return {"description": description, "size": size, "max_price": max_price}


def new_session(query: str, wardrobe: dict) -> dict:
    """Keep tool results and snapshots of the inputs actually passed to tools."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": deepcopy(wardrobe),
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
        "tool_calls": [],
    }


_STEP_NAMES = {
    "search": "search_listings (via MCP)",
    "outfit": "suggest_outfit",
    "card": "create_fit_card",
}


def _trace_stop(next_step: str, shown, exc: Exception) -> None:
    trace.step(_STEP_NAMES[next_step], inputs=shown,
               note=f"raised {type(exc).__name__}, stopping; earlier results kept")


def run_agent(query: str, wardrobe: dict) -> dict:
    """Choose each next tool from the last result, saving every result in state."""
    session = new_session(query, wardrobe)
    try:
        session["parsed"] = parse_query(session["query"])
    except ValueError as exc:
        session["error"] = str(exc)  # Parser messages are local, never provider bodies.
        trace.step("parse_query (local, no model)", inputs=query,
                   note="malformed size or budget, stopping before any tool")
        return session
    trace.step("parse_query (local, no model)", inputs=query,
               returned=json.dumps(session["parsed"]))

    next_step = "search"
    iterations = 0
    while True:
        iterations += 1
        try:
            trace.check_iterations(iterations)
        except RuntimeError:
            session["error"] = "Stopped at the loop limit. Check MAX_ITERATIONS in config.py."
            trace.step("check_iterations", inputs=iterations, note="loop limit, stopping")
            return session

        shown = None
        try:
            if next_step == "search":
                inputs = dict(session["parsed"])
                shown = json.dumps(inputs)
                session["tool_calls"].append({
                    "tool": "search_listings", "inputs": deepcopy(inputs),
                })
                # search_listings runs in mcp_server.py; the reply is decoded JSON.
                results = call_tool("search_listings", inputs)
                if not isinstance(results, list):
                    raise MCPError(f"search_listings returned {type(results).__name__}, not a list")
                session["search_results"] = results
                if not session["search_results"]:
                    session["error"] = (
                        "No listings matched those keywords, size, and budget. "
                        "Try broader keywords, another size, or a higher budget."
                    )
                    trace.step(_STEP_NAMES["search"], inputs=shown, returned=results,
                               note="branch: empty, stopping before suggest_outfit")
                    return session
                session["selected_item"] = deepcopy(session["search_results"][0])
                trace.step(_STEP_NAMES["search"], inputs=shown, returned=results,
                           note=f"branch: not empty, passing {session['selected_item']['id']} "
                                "to suggest_outfit")
                next_step = "outfit"

            elif next_step == "outfit":
                inputs = {
                    "new_item": session["selected_item"],
                    "wardrobe": session["wardrobe"],
                }
                shown = (f"new_item={inputs['new_item']['id']} ({inputs['new_item']['title']}), "
                         f"wardrobe={len(inputs['wardrobe'].get('items', []))} items")
                session["tool_calls"].append({
                    "tool": "suggest_outfit", "inputs": deepcopy(inputs),
                })
                session["outfit_suggestion"] = suggest_outfit(**inputs)
                if not session["outfit_suggestion"] or not session["outfit_suggestion"].strip():
                    session["error"] = "The model returned no outfit. Try the same search again."
                    trace.step(_STEP_NAMES["outfit"], inputs=shown, returned="(blank)",
                               note="no outfit, stopping before create_fit_card")
                    return session
                trace.step(_STEP_NAMES["outfit"], inputs=shown,
                           returned=session["outfit_suggestion"], note="next: create_fit_card")
                next_step = "card"

            elif next_step == "card":
                inputs = {
                    "outfit": session["outfit_suggestion"],
                    "new_item": session["selected_item"],
                }
                shown = (f"outfit=({len(inputs['outfit'])} chars from suggest_outfit), "
                         f"new_item={inputs['new_item']['id']}")
                session["tool_calls"].append({
                    "tool": "create_fit_card", "inputs": deepcopy(inputs),
                })
                session["fit_card"] = create_fit_card(**inputs)
                if not session["fit_card"] or not session["fit_card"].strip():
                    session["fit_card"] = None
                    session["error"] = "The model returned no caption. Try the same search again."
                trace.step(_STEP_NAMES["card"], inputs=shown,
                           returned=session["fit_card"] or "(blank)",
                           note="done" if session["fit_card"] else "no caption, stopping")
                return session

        except QuotaGuard as exc:
            _trace_stop(next_step, shown, exc)
            session["error"] = (
                "This session reached its model request budget. Stop the program, "
                "check the loop and SESSION_REQUEST_BUDGET in config.py, then "
                "restart when you are ready for a new session."
            )
            return session
        except MCPError as exc:
            # MCPError subclasses RuntimeError, so it must be caught first or
            # a broken search server would be reported as a model problem.
            _trace_stop(next_step, shown, exc)
            session["error"] = (
                "Could not reach the search tool, which runs as an MCP server "
                "(mcp_server.py). Run `python mcp_client.py` to check that the "
                "server starts and lists search_listings, then try again."
            )
            return session
        except (ModelUnavailable, RuntimeError) as exc:
            # The adapter can include provider diagnostics in exceptions. Never
            # send those bodies (which may contain request details) to the CLI.
            _trace_stop(next_step, shown, exc)
            session["error"] = (
                f"Could not finish the {next_step} step because the model is unavailable "
                "or its request limit was reached. Wait a moment and try again; "
                "if it persists, check your local key and model settings."
            )
            return session


def _show(session: dict) -> None:
    print(json.dumps(session, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Matching query: full session ===")
    _show(run_agent("vintage graphic tee under $30, size M", get_example_wardrobe()))
    print("\n=== Empty search: full session ===")
    _show(run_agent("designer ballgown size XXS under $5", get_example_wardrobe()))
