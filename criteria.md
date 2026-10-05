# Acceptance criteria — FitFindr

These targets were recorded before the tools and loop were implemented.
Criteria 1 and 2 come from the assignment. I asked Codex to draft reasonable
targets for 3–5; that assistance is also disclosed in the README.

For next unit's evaluation, turn caching off so repeated model calls are real
trials. Each trial starts a fresh session. The checks below describe how to
score a run; these are targets, not results.

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

Use `vintage graphic tee under $30, size M` with the example wardrobe for the
five tries. A pass has `error is None`, all three tool names in `tool_calls` in
order, and a nonempty `fit_card`.

**Why this target:** Search is local, but the two generation calls depend on
model availability and can return unusable text. Four of five allows one such
failure while requiring the full flow to work reliably most of the time.

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

Use `designer ballgown size XXS under $5` with the example wardrobe. Each pass
has only `search_listings` in `tool_calls`, `fit_card is None`, and an error
message naming at least one concrete change to keywords, size, or budget.

**Why this target:** This decision uses an empty Python list and never needs the
model. A failure here would mean the branch is wrong, so I expect all five.

## 3. The selected item reaches both later tools unchanged

Across five fresh runs of `vintage graphic tee under $30, size M` with the
example wardrobe, the entire listing dictionary in `search_results[0]` must
equal `selected_item` and the recorded `new_item` input to both `suggest_outfit`
and `create_fit_card` — 5 of 5 tries, with no second item prompt to the user.
A run that never reaches either later tool is a failure for this criterion.

**Why this target:** Item identity should not vary with the caption wording.
Comparing the whole dictionary catches a changed price or size even when the
ID stays the same. Five of five is deliberately strict, including the risk of
an interrupted model call; the state needs to support the complete chain.

## 4. The caption is short, specific, and grounded

For five uncached runs of `vintage graphic tee under $30, size M` with the
example wardrobe, at least 4 of 5 fit cards must satisfy all of these checks:
2–4 sentences, no more than 70 whitespace-separated words, one clear mention
of the selected item, its exact listed dollar price and platform each once,
and at least one clothing or accessory detail from `outfit_suggestion`.
The caption must not invent a brand, material, condition, discount, or shipping
claim absent from the selected listing. A missing card fails.

Count sentences by terminal `.`, `!`, or `?`, treating consecutive terminal
marks as one ending and ignoring a decimal point inside a price. Item wording
can be shortened if it unambiguously identifies the selected piece; platform
capitalization and trailing price zeros do not matter.

**Why this target:** The caption should sound like a post without making up
facts. I chose four of five because the model can vary length and wording;
requiring every check on the same card still makes this a meaningful target.

## 5. Search respects the size and price together

All returned listings must satisfy the requested size and inclusive maximum
price, and the expected listing below must be present, in 5 of 5 search tests:

| Description | Size | Maximum price | Expected ID |
|---|---|---|---|
| butterfly | M | 18 | lst_002 |
| flannel | XL | 22 | lst_003 |
| platform sneakers | 8 | 48 | lst_019 |
| jeans | W30 L30 | 38 | lst_001 |
| track jacket | M | 45 | lst_004 |

For this check, M accepts M, S/M, or M/L; XL accepts an XL token even with an
annotation; 8 accepts US 8 but not US 8.5; W30 L30 requires both tokens.
An empty result fails even though it contains no out-of-budget items.

**Why this target:** A cheap result is not useful if the size is wrong. These
checks use exact fields in the supplied data and do not call a model, so five
of five is reasonable. Requiring a known result also prevents an always-empty
search from passing.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
