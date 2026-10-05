# FitFindr

Submission repository: [ron2k1/RonilBasu-ai201-project2](https://github.com/ron2k1/RonilBasu-ai201-project2)

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
the search result in the session and gives a retry message. If the process has
used its whole request budget, the message says to check the loop and budget,
then restart the program. I am not adding a fourth tool or persistent style
memory this unit.

## Sample Run

The following output came from live Gemini calls during the build. The normal
cache was enabled for the full query; the session check immediately afterward
reused those responses.

```text
python app.py ask 'vintage graphic tee under $30, size M'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1: Pair the Y2K Baby Tee with the baggy straight-leg jeans, chunky white sneakers, and black crossbody bag. The fitted crop length of the butterfly tee balances the relaxed streetwear vibe of the high-waisted dark wash denim.

Outfit 2: Combine the Y2K Baby Tee with the wide-leg khaki trousers, vintage black denim jacket, and black combat boots. Layering the cropped denim jacket over the pink, purple, and white graphic top creates a fun mix of vintage Y2K and edgy grunge elements while keeping the silhouette balanced.

  Fit card: Channel a relaxed streetwear vibe by pairing the Y2K Baby Tee with baggy straight-leg jeans and chunky white sneakers. The fitted crop length of this butterfly print top balances the relaxed denim nicely. You can find this piece on depop for $18.

2 model calls this session, 1212 prompt + 168 output tokens
```

Each tool was also run directly, before wiring the loop:

```text
python -c "from tools import search_listings; print(search_listings('vintage graphic tee', size='M', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}]
```

```text
python -c "from tools import suggest_outfit; from utils.data_loader import load_listings, get_example_wardrobe; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1:
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top, Black cropped zip hoodie, and Chunky white sneakers.
Why it works: The fitted white tank balances the cropped black hoodie for a casual, sporty streetwear look that lets the classic medium wash denim stand out.

Outfit 2:
Style the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt and Black combat boots, finished with the Brown leather belt.
Why it works: Tucking the slouchy grey crewneck into the straight-leg jeans creates an effortless, cozy silhouette, while the combat boots and leather belt anchor the vintage aesthetic.
```

```text
python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('white tee and black Converse high-tops', load_listings()[0]))"
These vintage Levi's 501 jeans bring an effortless streetwear energy to any look. I would style them with a simple white tee and black Converse high-tops for an easy weekend vibe. You can find these classic denim bottoms listed on depop for $38.
```

The impossible query, `designer ballgown size XXS under $5`, returned:

```text
No listings matched those keywords, size, and budget. Try broader keywords, another size, or a higher budget.
```

Its session contained only `search_listings` in `tool_calls`; `selected_item`,
`outfit_suggestion`, and `fit_card` stayed `None`. On the matching run,
`search_results[0]`, `selected_item`, and both recorded `new_item` inputs were
equal, including the ID `lst_002`, size `S/M`, and price `18.0`.

To inspect those values or try an empty wardrobe:

```powershell
python app.py ask 'vintage graphic tee under $30, size M' --session
python app.py ask 'designer ballgown size XXS under $5' --session
python app.py ask 'vintage graphic tee under $30, size M' --empty-wardrobe --session
python -m unittest discover -s tests -v
```

The empty-wardrobe run completed all three tools and gave general suggestions.
The complete session output is in [results/build-agent-checks.txt](results/build-agent-checks.txt).
[results/build-tool-checks.txt](results/build-tool-checks.txt) also includes the
empty cases and three calls to `create_fit_card` on the same input with
`CACHE_ENABLED = False`; the three captions had different wording.

Build checks used Python 3.12.13 and the starter's `gemini-3.5-flash-lite` model.
`python test.py` passed all 10 environment checks, and all 25 offline unit tests
passed. The unit tests use real listing data and explicit mocked model responses
to check filtering, parsing, state, and branches. They do not establish the
five-trial caption-quality results for next unit. Those targets remain in
[criteria.md](criteria.md), committed before implementation.

## How I Used AI

I used Codex to implement, test, review, and document this project. These were
two specific parts of that work:

1. I asked it to finish FitFindr end to end using the assignment and starter.
   It built the tools and session loop, then its review found that ending a
   query with a period made a valid price or size look malformed. The parser
   was changed to allow sentence punctuation while still keeping decimal
   prices and shoe sizes intact, and regression tests were added.
2. I asked it to choose reasonable targets for the three original acceptance
   criteria. It drafted checks for exact item identity, a short grounded
   caption, and size plus price filtering. I used those drafts in `criteria.md`
   with the two supplied criteria and reasons for all five, and had them
   committed before implementation and model runs. The criteria are
   AI-assisted; I am not claiming I wrote them independently.

The sample output above is from actual terminal runs. The next-unit evaluation
sections below are intentionally left for the next unit.

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

       [x] criteria.md has five numbered criteria, each with a target
       [x] Each criterion has a reason underneath it
       [x] All five unit 3 sections above have real content
       [x] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [x] Planning Loop names the branch rule and agent.py::run_agent
       [x] Sample Run: one full query plus the three per-tool tests, as text
       [x] At least four new commits
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
