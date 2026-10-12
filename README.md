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

The sample output above is from actual terminal runs.

**Unit 4.** For the testing unit I used Claude Code, Anthropic's coding agent,
and gave it the unit 4 brief. It made the MCP move, added the trace calls and
the failure handlers, wrote the scenarios and the scorer, ran both evaluations
and drafted the unit 4 sections of this README. The unit 4 commits are its
work, done at my request. As with the criteria, I'm not claiming I did this
part independently. Three specific pieces:

1. **Pass/fail.** `run_eval.py` deliberately doesn't judge tries, so I had it
   turn each criterion into code (`score_run.py`) and commit that before the
   first run, so the history shows the rules came first. The scorer was wrong
   once. It counted "a denim jacket layered over top" as a second naming of
   the tee. Claude Code reading every caption in full, instead of trusting the
   scorer, caught it, and the fix went in its
   own commit, with the original 2/5 left visible in the commit before it.
2. **Failure messages.** After triggering the three failure modes, it had a
   separate agent read each message cold, as a user who can't see the code.
   That read said the empty-wardrobe run "in practice gives me nothing to
   try", because nothing said the outfit used pieces I don't own. It also said
   the model-unavailable message "covers two different problems", a bad key
   and a rate limit, so I couldn't tell whether waiting would help. Both
   changed: the empty wardrobe now gets a note, and the two causes get
   separate messages. The before and after transcripts are in
   [results/failure-modes.md](results/failure-modes.md).
3. **Choosing the improvement.** It tallied every check across all 15
   captions from the matching query before picking a fix. That showed one
   cause, the double naming, so the single allowed change went to the caption
   prompt, not to anything that was already passing.
4. **Checking the write-up.** A separate review agent checked every number
   and quote in these sections against the committed result files and git
   history. The counts held up. It found that an earlier draft said captions
   were read "by hand" in my voice. At that point Claude Code had read them,
   not me, so the wording was fixed. I have since read all 30 myself. It also
   found one quote that wasn't verbatim, two claims stated more broadly than
   the data, and the overconfident error message in What's Still Broken
   item 6, which was reworded after the after-run. All are corrected or
   listed.

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

Unit 4 was carried out by Claude Code at my request (see How I Used AI).
Where these sections say captions were read, Claude Code read each full
caption, not just the scorer's verdict. I then read all 30 matching-query
captions myself, 15 before and 15 after. The judgment calls noted below are
Claude Code's calls.

`python run_eval.py --label before`, 2026-10-11 22:46, gemini-3.5-flash-lite
at temperature 0.9, cache off, 50 real model calls. Each criterion has its own
scenario in [scenarios.py](scenarios.py), so each row is five tries of its own.
Criterion 5's five tries are the five searches in its table, each run through
the whole agent, so each one is a real MCP call.
Raw log: [results/run_2026-10-11_2246_before.md](results/run_2026-10-11_2246_before.md),
with the same tries as data in the `.json` beside it.

One environment note. Both eval runs, before and after, used this machine's
global Python 3.14.3 (mcp 1.26.0, google-genai 1.69.0), not the project's
`.venv` (Python 3.12.13, mcp 1.30.0, google-genai 1.75.0). That wasn't noticed
until `test.py` flagged it afterwards. The code, model, prompt and
temperature were the same, and the two runs share the interpreter, so the
before/after comparison is like for like. In the `.venv`, all 31 unit tests
and all 10 `test.py` checks pass, and the Loop Trace below was recaptured
there.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item reaches both later tools unchanged | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Caption is short, specific, and grounded | 4 of 5 | PASS | PASS | FAIL | PASS | FAIL | MISSED (3/5) |
| 5. Search respects the size and price together | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

PASS/FAIL comes from [score_run.py](score_run.py), which turns each criterion
into code and was committed (8beda05) before this run started. Claude Code
also read every caption in full. That read found one scorer false positive:
try 2's "A cropped vintage denim jacket layered **over top**" uses *top* as an adverb, not as a name
for the tee. The committed scorer's original 2/5 is in 2e205c4. The fix,
3557cd3, changed that one cell and no verdict. Per-try reasons:
[results/score_2026-10-11_2246_before.md](results/score_2026-10-11_2246_before.md).

**Real output from one try**, criterion 4 try 3, from `run_eval.py::write_report`
(the loop is `agent.py::run_agent`, the caption is `tools.py::create_fit_card`):

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 1

Outfit suggestion:
Outfit 1: Pair the Y2K Baby Tee with the Baggy straight-leg jeans, dark wash and Chunky white sneakers. This balances the fitted, cropped butterfly tee with relaxed denim for an authentic Y2K streetwear vibe.

Outfit 2: Combine the Y2K Baby Tee with the Wide-leg khaki trousers, Vintage black denim jacket, and Black combat boots. The pink and purple butterfly graphic pops against earth tones, while the jacket and boots add a nice grunge contrast.

Fit card:
Channel true Y2K streetwear energy by pairing this butterfly baby tee with relaxed dark wash straight-leg jeans and chunky white sneakers. You could grab this cute top for $18 on depop to complete your nostalgic wardrobe.

Trace:
[1] parse_query (local, no model)
      in:  vintage graphic tee under $30, size M
      out: {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
[2] search_listings (via MCP)
      in:  {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
      out: 1 items: Y2K Baby Tee — Butterfly Print
      →    branch: not empty, passing lst_002 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_002 (Y2K Baby Tee — Butterfly Print), wardrobe=10 items
      out: Outfit 1: Pair the Y2K Baby Tee with the Baggy straight-leg jeans, dark wash and Chunky white sneakers. This b…
      →    next: create_fit_card
[4] create_fit_card
      in:  outfit=(450 chars from suggest_outfit), new_item=lst_002
      out: Channel true Y2K streetwear energy by pairing this butterfly baby tee with relaxed dark wash straight-leg jean…
      →    done
```

Scored by `score_run.py::check_4`: `FAIL — item named 2x | 2 sent, 36 words,
named 2x, price 1x, platform 1x, details ['jeans', 'sneakers']`. The card names
the tee as "this butterfly baby tee" and again as "this cute top". Everything
else on the card passes.

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
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | Every try had `error` None, `tool_calls` in the order search_listings, suggest_outfit, create_fit_card, and a nonempty `fit_card`. |
| 2 | Impossible query stops before the second tool | 5 of 5 | MET (5/5) | Every try had only `search_listings` in `tool_calls`, `fit_card` None, and the error "Try broader keywords, another size, or a higher budget". It used 0 model calls, as the branch should. |
| 3 | Selected item reaches both later tools unchanged | 5 of 5 | MET (5/5) | The whole lst_002 dict compared equal across `search_results[0]`, `selected_item`, and the `new_item` input recorded for both later tools. |
| 4 | Caption is short, specific, and grounded | 4 of 5 | MISSED (3/5) | Each card was checked for 2–4 sentences, at most 70 words, exactly one naming of the item (the revision under criterion 4), price and platform once each, an outfit detail, and no invented claim. Tries 3 and 5 named the tee twice. Claude Code also read all five in full. |
| 5 | Search respects the size and price together | 5 of 5 | MET (5/5) | Each of the five searches returned only listings within the size rule and price ceiling copied from the criterion, and the expected ID was present every time. |

**Diagnoses**

**Criterion 4 missed, 3 of 5. Place: the model's output, shaped by the prompt
in `tools.py::create_fit_card`.**

The tool, branch and session all worked. Criterion 3 shows the right item
reached the caption step every time. The two failed cards broke one rule
only: each named the item twice. A pattern goes beyond those five tries.
Criteria 1, 3 and 4 all run the same query, so the run produced 15 captions.
Across all 15, length, sentence count, price, platform, outfit detail and
invented claims never failed. The double naming did, on 9 of 15 when
read in full. Every time, the first naming is the subject of sentence 1 ("pairing
this butterfly baby tee with...") and the second is a descriptive re-naming
later on. It lands in one of two places:

- **The price-and-platform sentence (5 of 9):** "You could grab *this cute
  top* for $18 on depop", "You can score *this graphic top* on depop for $18".
  The prompt asks for the item, its price and its platform "once" each, in one
  list. The model reads that as one closing line, "find [item] on [platform]
  for [price]", and fills the [item] slot again. Some passing cards used
  "this piece" in that slot.
- **A sentence borrowed from the outfit (4 of 9):** "*The fitted cropped
  graphic top* balances the voluminous denim". The prompt hands over the
  whole outfit suggestion, and its "why it works" lines name the tee again.
  In try 5 the outfit says "The fitted cropped top balances the voluminous
  dark denim" and the caption copies the sentence, second naming included.

"Mention the selected item once (you may shorten its title)" tells the model
to mention the item, but nothing caps it at one or says what to call the item
afterwards. The model treats "once" as "include it". This is one problem
across 9 captions, not 9 separate problems.

Two notes on how it was scored. Try 4 says "scout this butterfly print for
$18". That refers to the item with words from its title. The written rule
counts only the item's noun (tee, t-shirt, top) as a naming, so the rule was
followed and try 4 counted as a pass. Under a stricter reading try 4 fails, which makes 2/5, still
MISSED. Second, the scorer first counted try 2 as a fail because of "layered
over top". That was fixed in the open, as described under the table.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Both from `python app.py ask '<query>' --trace`, run in the project's `.venv`
(Python 3.12.13) with the cache off, on the final code (after the
improvement). The trace is printed by `trace.py::step`, called from
`agent.py::run_agent` at each step. Step 2 is the MCP call.

**Happy path**: `python app.py ask 'vintage graphic tee under $30, size M' --trace`

```
[1] parse_query (local, no model)
      in:  vintage graphic tee under $30, size M
      out: {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
[2] search_listings (via MCP)
      in:  {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
      out: 1 items: Y2K Baby Tee — Butterfly Print
      →    branch: not empty, passing lst_002 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_002 (Y2K Baby Tee — Butterfly Print), wardrobe=10 items
      out: Outfit 1: Y2K Streetwear Pair your Y2K Butterfly Baby Tee with the Baggy straight-leg jeans, dark wash and Chu…
      →    next: create_fit_card
[4] create_fit_card
      in:  outfit=(717 chars from suggest_outfit), new_item=lst_002
      out: I found this Y2K Butterfly Baby Tee on depop for $18. Pair it with baggy dark-wash jeans and chunky white snea…
      →    done

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1: Y2K Streetwear
Pair your Y2K Butterfly Baby Tee with the Baggy straight-leg jeans, dark wash and Chunky white sneakers. Add the Vintage black denim jacket and Black crossbody bag.
Why it works: The fitted crop of the baby tee balances the loose, high-waisted fit of the dark denim for an authentic Y2K streetwear silhouette, while the white sneakers tie in the tee's white base.

Outfit 2: Casual Contrast
Pair the butterfly tee with the Wide-leg khaki trousers and Black combat boots. Throw on the Black cropped zip hoodie.
Why it works: Pairing the feminine, graphic baby tee with utilitarian khaki trousers and rugged combat boots creates a cool, balanced contrast that highlights the vintage Y2K style.

  Fit card: I found this Y2K Butterfly Baby Tee on depop for $18. Pair it with baggy dark-wash jeans and chunky white sneakers for an effortless streetwear look. Throw on a black denim jacket and a crossbody bag to complete this nostalgic outfit.

2 model calls this session, 1311 prompt + 212 output tokens
```

**Empty search**: `python app.py ask 'designer ballgown size XXS under $5' --trace`

```
[1] parse_query (local, no model)
      in:  designer ballgown size XXS under $5
      out: {"description": "designer ballgown", "size": "XXS", "max_price": 5.0}
[2] search_listings (via MCP)
      in:  {"description": "designer ballgown", "size": "XXS", "max_price": 5.0}
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  No listings matched those keywords, size, and budget. Try broader keywords, another size, or a higher budget.

0 model calls this session
```

The empty trace stops after step 2 with 0 model calls, and the happy trace
goes on to steps 3 and 4. The branch decision is the `→` line under step 2 in
each.

**Failure modes, triggered on purpose.** Full transcripts, each with its
trace, are in [results/failure-modes.md](results/failure-modes.md).

| Failure | How I triggered it | What happens now | Change |
|---|---|---|---|
| Empty search | `designer ballgown size XXS under $5` | Stops after search with 0 model calls and names three things to change | None needed, it was handled in unit 3 |
| Empty wardrobe | `--empty-wardrobe` | The outfit uses suggested pieces, and a `Note:` line says they aren't owned and to add items | Added the note (d68a093). Shown in 5 of 5 tries in both eval runs. |
| Model unavailable | One character of `GEMINI_API_KEY` changed in `.env`, restored after the run, SHA-256 matched | Stops at `suggest_outfit`, keeps the search result, and says to check the key and connection, then to try again in a minute if both are fine | Split from the rate-limit message (d68a093). Reworded after the eval runs, because the same error also covers a temporary overload (What's Still Broken 6) |
| Search server unreachable (extra, from the MCP move) | `mcp_client.SERVER` pointed at a missing file for one run | Says the MCP search server didn't start and how to check it | New `MCPError` branch. Without it, the error would have been reported as a model failure, because `MCPError` subclasses `RuntimeError`. |

In the trace, the two errors show as `raised X, stopping; earlier results kept`
at the step where they stopped. The empty search shows `branch: empty`, and
the empty wardrobe shows `empty wardrobe: general advice, notice saved`.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

`search_listings` now runs on an MCP server. `mcp_server.py` registers it with
FastMCP over stdio and puts each parameter's description into the tool schema.
`agent.py::run_agent` calls `mcp_client.call_tool("search_listings", inputs)`
instead of importing the function. `suggest_outfit` and `create_fit_card` stay
local. The rewire worked on the first try. [results/mcp-check.txt](results/mcp-check.txt)
holds the evidence:

- `python mcp_client.py` lists the tool with its schema.
- 11 inputs, including the five criterion 5 searches and both empty cases,
  returned identical results direct and over MCP, and prices came back as floats.
- The happy-path trace above names step 2 `search_listings (via MCP)`.

Two things behave differently afterwards:

1. **Speed.** Each search now takes about 620–660 ms, because the client starts
   `mcp_server.py` as a new process on every call. The direct call took
   almost no time. With one search per query this doesn't matter. A loop
   that searched many times would need one session kept open.
2. **Errors.** A new failure exists: the server not starting. `run_agent` now
   catches `MCPError` and says the search tool (MCP) is unreachable, instead
   of blaming the model. This case is in [results/failure-modes.md](results/failure-modes.md).
   One rough edge is left. An exception raised *inside* the tool, such as a
   negative `max_price`, arrives as `unhandled errors in a TaskGroup (1
   sub-exception)`, with the real reason buried two `ExceptionGroup`s deep.
   The agent can't trigger this, because `parse_query` never produces a
   negative price. The brief allows only the MCP move and one improvement as
   system changes, so I recorded this rather than fixing it.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** one instruction in the `create_fit_card` prompt
(`tools.py`, commit 10391ce). It replaced:

> Mention the selected item once (you may shorten its title), its exact price
> $18 once, and its platform depop once.

with:

> Name the selected item exactly once, in the first sentence (you may shorten
> its title). After that, do not name or re-describe it with any noun; call it
> only "it" or "this piece". That includes the sentence with its price and
> platform, and any line you reuse from the outfit suggestion. Give its exact
> price $18 once and its platform depop once.

It says where the one naming goes and what to call the item afterwards. It
names both places the second naming used to land. It uses no garment word,
so it isn't tuned to the tee this query happens to select. The model,
temperature, inputs and scorer stayed the same. A new offline test,
`test_fit_card_prompt_caps_the_item_at_one_naming`, pins the instruction.

**Which failure it was meant to fix:** criterion 4, MISSED at 3/5. Every
failed card named the item twice. The second naming came in the
price-and-platform sentence or in a line copied from the outfit text (see
Diagnoses).

### Run Log — After

`python run_eval.py --label after`, 2026-10-11 22:54, same settings and the
same interpreter as before: gemini-3.5-flash-lite, temperature 0.9, cache off,
50 real model calls.
Scored by the same `score_run.py` (3557cd3). Raw log:
[results/run_2026-10-11_2254_after.md](results/run_2026-10-11_2254_after.md).
Per-try reasons: [results/score_2026-10-11_2254_after.md](results/score_2026-10-11_2254_after.md).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item reaches both later tools unchanged | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Caption is short, specific, and grounded | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search respects the size and price together | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Before and after, side by side:

| Criterion | Before | After |
|---|---|---|
| 1. Matching query completes all three tools | MET (5/5) | MET (5/5) |
| 2. Impossible query stops before the second tool | MET (5/5) | MET (5/5) |
| 3. Selected item reaches both later tools unchanged | MET (5/5) | MET (5/5) |
| 4. Caption is short, specific, and grounded | **MISSED (3/5)** | **MET (5/5)** |
| 5. Search respects the size and price together | MET (5/5) | MET (5/5) |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

It fixed what it was aimed at, and it caused a new problem that criterion 4
doesn't measure.

**What it fixed.** Criterion 4 went from 3/5 to 5/5, and a full read of each
caption agrees with all five passes. Five tries can move a lot by chance, so
Claude Code also counted across all 15 captions the matching query produced (criteria 1, 3 and 4
share it). Double naming fell from 9 of 15 to 1 of 15. The one left is
criterion 1 try 1, "the fitted silhouette of the top". The other checks
stayed clean in both runs, and criteria 1, 2, 3 and 5 held at 5/5. A typical
after card:

> Channeling an edgy Y2K streetwear vibe, this Y2K Baby Tee brings a playful
> pop to any daytime look. Pair it with baggy dark wash jeans and chunky black
> combat boots to balance the fitted silhouette. You can score it for $18 on
> depop.

One judgment call: criterion 4 try 2 says finding it for $18 "feels like an
absolute steal". That was read as an opinion, not an invented discount,
because it claims no markdown or sale. Counted the other way, criterion 4 is 4/5,
still MET.

**What it made worse.** Reading the after captions turned up a new pattern.
7 of 15 now claim a purchase happened, 6 of them in a haul-post opener:
"Scored this Y2K Baby Tee on depop for $18", "I just scored this Y2K
Butterfly Baby Tee". The seventh says it in sentence 2: "I scored it on depop
for $18". In thrift slang, "scored" means bought. The prompt has forbidden
purchase claims since unit 3. Before the change, 0 of 15 made one. They said
"You can score this piece" or "You could grab", which invite the reader
instead. The fix itself is the mechanism, at least for the six openers. The
name has to go in sentence one and can't come back in the price line, so the
model packs item, platform and price into one opener, and in this voice the
shortest way to do that is a past-tense haul line. Criterion 4's invented-claim list (brand, material, condition,
discount, shipping) doesn't include purchase claims, so the 5/5 doesn't see
it. It was found by reading the captions, not from the table. The Loop Trace
card, captured separately afterwards, opens the same way: "I found this Y2K
Butterfly Baby Tee on depop for $18."

So the verdict moved from MISSED to MET, and the captions really do name the
item once now. But they are worse at one rule the tool was already supposed
to follow.


---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

All five criteria are met after the improvement, so nothing here is a missed
target. These problems are still real:

1. **The captions now claim a purchase (7 of 15 after, 0 before).** My fix
   caused this (see above). Next I'd change the opener: name the item in
   sentence one, but put price and platform in a later sentence that offers
   it to the reader ("Find it on depop for $18"). That keeps the one naming
   and removes the reason to write "Scored this X for $18". I stopped because
   the brief allows one improvement, and a second prompt change needs its own
   before and after run to be measured properly. I'd also add purchase claims
   to criterion 4's invented-claim list for next time. I didn't change the
   criterion now, because adding a check after seeing the results is moving
   the goalposts.
2. **One double naming remains (1 of 15).** A prompt instruction made it rare
   but can't rule it out. The way to rule it out is a check after generation
   that counts namings and retries once. That needs the noun a caption
   would use ("tee"), and the listing only has a broad category ("tops"), so
   it's real work and I didn't start it.
3. **Criterion 4 tests one item.** All five tries caption lst_002, so the
   naming rule in `score_run.py` only knows that item's nouns. Captions for a
   listing with a brand or a vaguer title, like the Wrangler jacket in the
   empty-wardrobe runs, aren't measured. A better test would rotate through
   several listings the way criterion 5 rotates searches.
4. **The grounding check is a word list.** It catches named brands, materials
   and stock phrases. It found nothing in either run, but reading all 30
   captions in full did the real work, and that doesn't scale past a run this
   size. The list can also misfire on ordinary words. "delivers Y2K energy"
   would count as a shipping claim, "mint green" as a condition, "I guess" or
   "the colors mesh" as a brand or material. In the naming rule, "top it off"
   would count as naming the item. None of these came up in either run, so no
   cell changes, but a bigger test would need a real classifier or a human
   reader.
5. **Two MCP rough edges** (see the MCP note). Each search starts a new server
   process (~640 ms). An error raised inside the tool arrives as "unhandled
   errors in a TaskGroup" with the real message lost. The agent can't trigger
   the second today, but any new input path could.
6. **The model-unavailable message can't say which problem it hit.**
   `generate.py` turns every error that isn't a rate limit into
   `ModelUnavailable`. That covers a bad key, a temporary 503 "model is
   overloaded", and a blank answer, which `suggest_outfit` and
   `create_fit_card` raise as the same error. The message used to say
   "waiting won't fix this one", which is wrong for the last two. A review
   found this after the after-run, and I had the message reworded anyway:
   "Check that GEMINI_API_KEY in .env is correct and that you're online. If
   both are fine, the model may be overloaded, so try again in a minute." That
   goes past the brief's limit of the MCP move plus one improvement, so it
   isn't counted as the improvement. It changes only that message's text, and
   no try in either eval run reached that branch, so the before and after
   numbers are unaffected. The reworded message, triggered with a bad key, is
   in failure-modes.md. The real fix is a separate error type for each cause,
   so the message can name the one that happened. The same review found the
   agent's own "The model returned no outfit" branch can never run, because
   the tool raises first. That branch is still there.


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

       [x] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [x] Run Log — Before, five criteria, five tries each
       [x] Real output pasted underneath, naming file and function
       [x] A verdict on every criterion
       [x] A diagnosis for every miss, naming a place AND a mechanism
       [x] Loop Trace, with the MCP call visible in it
       [x] All three failure modes triggered and handled
       [x] One improvement, with Run Log — After in the same format
       [x] What's Still Broken
       [x] At least four new commits
       [x] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
