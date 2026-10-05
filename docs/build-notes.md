# FitFindr build notes

## Plan

1. Completed: inspect the starter, read the data, and prepare Python 3.12.
2. Completed: specify the three tools and the planning rule.
3. Completed: commit five acceptance criteria before implementing the tools.
4. **In progress:** build and check each tool, then connect the loop and session.
5. Record real runs, review the changes, and push the submission fork.

## Data notes

The starter includes 40 sample listings, not live marketplace inventory. I read
the first six records in full. Their fields are `id`, `title`, `description`,
`category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and
`platform`. Search can check keywords, sizes, and listed prices; it cannot check
shipping costs or whether something is still available.

| ID | Item | Size | Price | Platform |
|---|---|---|---|---|
| lst_001 | Vintage Levi's 501 Jeans | W30 L30 | $38 | depop |
| lst_002 | Y2K Baby Tee — Butterfly Print | S/M | $18 | depop |
| lst_003 | Oversized Flannel Shirt | XL (oversized) | $22 | thredUp |
| lst_004 | 90s Track Jacket | M | $45 | poshmark |
| lst_005 | Corduroy Wide-Leg Pants | W28 | $32 | depop |
| lst_006 | Graphic Tee — 2003 Tour Bootleg Style | L | $24 | depop |

The wardrobe is a dictionary with an `items` list. Each item has `id`, `name`,
`category`, `colors`, `style_tags`, and optional `notes`. An empty wardrobe is
`{"items": []}`. Most listings have no brand, so prompts cannot assume one exists.

Size matching needs complete tokens: M can match S/M, but L cannot match XL,
S cannot match US 9, and shoe size 8 cannot match 8.5. One Size does not guarantee
a match for a specific clothing size. A description can mention another item
as styling advice, so title and style tags should carry more weight in ranking.

## Starting point

This repository retains the CodePath FitFindr starter history at `69997cf`.
The earlier project-one RAG repository is separate and stays unchanged. This
FitFindr repository is the one to keep for both units.

The initial CLI check ran before implementation:

```text
python app.py ask 'vintage graphic tee under $30'

  The planning loop isn't built yet — see the TODO in agent.py.

0 model calls this session
```
