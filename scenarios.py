"""
The runs the test needs, one scenario per criterion in criteria.md.

`run_eval.py` runs everything here five times and writes the run log — five
because the criteria are written out of five. `score_run.py` then scores each
try against the criterion its scenario names.

Criteria 1, 3 and 4 all name the same query. Each still gets its own scenario,
so every criterion is scored on five runs of its own rather than sharing one
set of five.

Criterion 5 is five *different* search tests (the table in criteria.md), so
its scenario lists five queries and try N runs the Nth one. Each goes through
the whole agent, so the search is the MCP call the agent really makes.
"""

MATCHING = "vintage graphic tee under $30, size M"

SCENARIOS = [
    {
        "name": "matching query completes all three tools",
        "query": MATCHING,
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        "name": "impossible query stops before suggest_outfit",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        "name": "selected item reaches both later tools unchanged",
        "query": MATCHING,
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "caption is short, specific, and grounded",
        "query": MATCHING,
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "search respects the size and price together",
        # One per row of the criterion 5 table, in the same order.
        "queries": [
            "butterfly size M under $18",
            "flannel size XL under $22",
            "platform sneakers size 8 under $48",
            "jeans size W30 L30 under $38",
            "track jacket size M under $45",
        ],
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def query_for(scenario: dict, attempt: int) -> str:
    """The query for try `attempt` (1-based): the fixed query, or the Nth of a list."""
    queries = scenario.get("queries")
    if queries:
        return queries[(attempt - 1) % len(queries)]
    return scenario["query"]


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        queries = scenario.get("queries")
        if queries is not None:
            if not queries or not all(isinstance(q, str) and q.strip() for q in queries):
                problems.append(f"scenario {i} has an empty query in its list")
        elif not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
