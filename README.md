# FitFindr

## What This Does

FitFindr takes a request like “a vintage graphic tee under $30, size M” and
searches the 40 sample listings included in the starter. It picks a matching
item, uses the example wardrobe to suggest an outfit, and writes a short caption
with the item's price and platform. If nothing matches, it stops and tells me
what to change. It runs from the terminal; these are bundled listings, so it
does not check live availability or buy anything.

Use Python 3.11–3.13. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Add your GEMINI_API_KEY to .env locally.
python test.py
python app.py ask 'vintage graphic tee under $30, size M'
```

Keep the single quotes around queries containing dollar amounts. The full
starter command reference is [RUNNING.md](RUNNING.md). Keep this repository for
next unit: the criteria and commit history need to stay together.

## Tool Inventory

### `search_listings`

- **What it does:** Loads the bundled listings with `load_listings()` and filters by description, size, and maximum price.
- **Inputs:** `description` (`str`), `size` (`str | None`, default `None`), `max_price` (`float | None`, default `None`).
- **Returns:** Up to `config.SEARCH_RESULT_LIMIT` complete listing dictionaries, each with `id`, `title`, `description`, `category`, `style_tags` (`list[str]`), `size`, `condition`, `price` (`float`), `colors` (`list[str]`), `brand` (`str | None`), and `platform`. Better title/tag matches come first, with lower price and then ID breaking ties.
- **When it has nothing:** Returns `[]` for no match or a description with no searchable words. Invalid negative/nonfinite price ceilings raise `ValueError`.

Every meaningful description word must occur in the listing's title,
description, category, tags, colors, or brand, ignoring case and punctuation.
Common request words such as “looking for” are removed. At least one word must
occur outside the description so a passing mention alone does not qualify.
Title, tags, and the other structured text fields count more toward ranking
than description text. This is keyword matching, not a synonym search.

The ceiling is inclusive and applies to the listed price only. M matches M,
S/M, and M/L; L does not match XL. Shoe size 8 matches US 8, not US 8.5. W30
matches W30 or W30 L30; requesting W30 L30 requires both parts. One Size matches
only an explicit One Size request. Sizes are label matches, not a fit guarantee.

### `suggest_outfit`

- **What it does:** Calls the starter's `generate()` adapter for one or two outfit ideas using the selected listing and supplied wardrobe.
- **Inputs:** `new_item` (`dict`, one complete listing), `wardrobe` (`dict` with `items: list[dict]`; each wardrobe item has `id`, `name`, `category`, `colors`, `style_tags`, and optional `notes`).
- **Returns:** A nonempty `str` naming the selected item and specific wardrobe pieces, with a brief explanation of how they go together.
- **When it has nothing:** With `{"items": []}`, asks the model for general styling advice and labels suggested pieces as ideas, not things the user owns. With no selected item, returns `Choose a listing before asking for an outfit.` A blank model response raises `ModelUnavailable` rather than pretending it is an outfit.

### `create_fit_card`

- **What it does:** Calls `generate()` to turn the outfit and selected listing into a casual caption.
- **Inputs:** `outfit` (`str`), `new_item` (`dict`, the same complete listing).
- **Returns:** A nonempty `str`; the prompt requests 2–4 sentences, at most 70 words, the item, its exact listed price and platform once each, and an outfit detail. This is a quality target to test, not a guaranteed sentence count.
- **When it has nothing:** For blank outfit text, returns `No outfit to caption. Generate an outfit suggestion first.` For no item, returns `Choose a listing before creating a fit card.` Neither case calls the model. A blank model response raises `ModelUnavailable`.

Both model tools use the starter's cache and rate-limit pacing. Provider failure
is an exception at the tool boundary and a readable error at the agent boundary.
No hardcoded successful model responses are used in the application.

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, save a message
suggesting broader keywords, another size, or a higher budget and stop. Otherwise,
select the first result and call `suggest_outfit`, then use that returned outfit
and the same item to call `create_fit_card`.

**Where it lives:** `agent.py::run_agent`, with a `while` loop and a separate
search, outfit, and card step. Each iteration checks `trace.check_iterations`.

**How the query is parsed:** Regular expressions extract `size M`, `in size M`,
`size US 8`, `size W30 L30`, or `size One Size`, and a ceiling such as `under $30`,
`below 30`, `up to $30`, or `max price 30`. A bare `$30` is also a ceiling.
Those spans are removed before keyword matching. The parser does not ask the
model and does not ask the user to repeat the item.

**What moves through the session:** `query` becomes `parsed`; search output goes
into `search_results`; the first entry becomes `selected_item`. The outfit tool
reads `selected_item` and `wardrobe` from the session, and its output becomes
`outfit_suggestion`. The caption tool reads that value and `selected_item` back
from the session, then saves `fit_card`. `tool_calls` records the tool names and
actual input snapshots so item identity can be checked. `error` explains an
early stop, while unfinished result fields remain `None`.

**Stretch declared before implementation:** A second branch stops before the
caption when outfit generation is empty or the model is unavailable. It keeps
the search result in the session and gives a retry message. I am not adding a
fourth tool or persistent style memory this unit.

## Sample Run

Implementation and real terminal outputs will be added after the tool checks.
The starter baseline and data notes are in [docs/build-notes.md](docs/build-notes.md).

## How I Used AI

I used Codex for implementation, tests, and documentation as well as review.
I also asked it to choose reasonable targets for the three original criteria;
those targets were drafted with AI assistance. The completed build will include
two concrete examples of what that assistance changed.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
