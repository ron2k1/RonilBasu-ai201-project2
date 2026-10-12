# Failure modes, triggered on purpose (unit 4, Milestone 2)

Recorded 2026-10-11 with search over MCP and the trace on. Every block is
real terminal output. Model runs used `AI201_CACHE=0` or a query not asked
before, so none of them were answered from the build cache.

## 1. Empty search

```text
python app.py ask 'designer ballgown size XXS under $5' --trace
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

Already handled in unit 3 and unchanged: it stops after search, before any
model call, and names three things to change.

## 2. Empty wardrobe

First trigger:

```text
python app.py ask 'denim jacket under $50' --empty-wardrobe --trace
(running with an empty wardrobe)
[1] parse_query (local, no model)
      in:  denim jacket under $50
      out: {"description": "denim jacket", "size": null, "max_price": 50.0}
[2] search_listings (via MCP)
      in:  {"description": "denim jacket", "size": null, "max_price": 50.0}
      out: 1 items: Denim Jacket — Light Wash, Cropped
      →    branch: not empty, passing lst_007 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_007 (Denim Jacket — Light Wash, Cropped), wardrobe=0 items
      out: With an empty wardrobe, this Wrangler light wash cropped denim jacket is a versatile streetwear staple. Its st…
      →    next: create_fit_card
[4] create_fit_card
      in:  outfit=(514 chars from suggest_outfit), new_item=lst_007
      out: This Wrangler light wash cropped denim jacket gives off an effortless vintage vibe. Layer it over a black turt…
      →    done

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

  Outfit:   With an empty wardrobe, this Wrangler light wash cropped denim jacket is a versatile streetwear staple. Its structured shoulders and vintage vibe make it a great blank canvas for layering. 

General styling advice: Lean into its cropped cut by pairing it with high-waisted silhouettes to balance proportions.

Combinations to consider:
1. Suggestion: A black turtleneck bodysuit, high-waisted wide-leg trousers, and white sneakers.
2. Suggestion: A floral slip dress and combat boots for a classic grunge contrast.

  Fit card: This Wrangler light wash cropped denim jacket gives off an effortless vintage vibe. Layer it over a black turtleneck bodysuit and high-waisted wide-leg trousers for a cool streetwear look. You can find this piece on poshmark for $42.

2 model calls this session, 629 prompt + 155 output tokens
```

No crash and no empty string, but see the message check below: it reads like
a normal result, never says the empty wardrobe is why it names pieces the user
doesn't own, and never says what fixes that. The agent now saves a fixed
`notice` whenever the wardrobe has no items, and `app.py` prints it:

```text
python app.py ask 'denim jacket under $50' --empty-wardrobe --trace
(running with an empty wardrobe)
[1] parse_query (local, no model)
      in:  denim jacket under $50
      out: {"description": "denim jacket", "size": null, "max_price": 50.0}
[2] search_listings (via MCP)
      in:  {"description": "denim jacket", "size": null, "max_price": 50.0}
      out: 1 items: Denim Jacket — Light Wash, Cropped
      →    branch: not empty, passing lst_007 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_007 (Denim Jacket — Light Wash, Cropped), wardrobe=0 items
      out: With an empty wardrobe, this Wrangler light wash cropped denim jacket is a versatile streetwear piece. Its str…
      →    empty wardrobe: general advice, notice saved; next: create_fit_card
[4] create_fit_card
      in:  outfit=(523 chars from suggest_outfit), new_item=lst_007
      out: Channel a cool streetwear vibe by styling this Wrangler denim jacket with a black slip dress and chunky boots …
      →    done

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark

  Outfit:   With an empty wardrobe, this Wrangler light wash cropped denim jacket is a versatile streetwear piece. Its structured shoulders and vintage vibe make it a great blank canvas. 

General styling advice: Pair this cropped cut with high-waisted bottoms to balance proportions, or layer it over dresses and hoodies. 

Here are a few combinations to consider:
1. Suggestion: A black slip dress and chunky boots for an edgy contrast.
2. Suggestion: High-waisted wide-leg trousers and a fitted white tee for a classic, casual look.

  Fit card: Channel a cool streetwear vibe by styling this Wrangler denim jacket with a black slip dress and chunky boots for an edgy contrast. The cropped silhouette features structured shoulders that pair effortlessly with high-waisted pieces. You can find this versatile layer on poshmark for $42.

  Note:     Your wardrobe is empty, so this outfit uses suggested pieces you don't own. Add a few items to your wardrobe to get outfits built from your own clothes.

2 model calls this session, 636 prompt + 167 output tokens
```

## 3. Model unavailable (one character of GEMINI_API_KEY changed in .env, then restored)

First trigger, with the handler as it was in unit 3:

```text
python app.py ask 'corduroy pants under $40' --trace
(.env key changed in one character; query: 'corduroy pants under $40')
[1] parse_query (local, no model)
      in:  corduroy pants under $40
      out: {"description": "corduroy pants", "size": null, "max_price": 40.0}
[2] search_listings (via MCP)
      in:  {"description": "corduroy pants", "size": null, "max_price": 40.0}
      out: 1 items: Corduroy Wide-Leg Pants — Rust
      →    branch: not empty, passing lst_005 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_005 (Corduroy Wide-Leg Pants — Rust), wardrobe=10 items
      →    raised ModelUnavailable, stopping; earlier results kept

  Could not finish the outfit step because the model is unavailable or its request limit was reached. Wait a moment and try again; if it persists, check your local key and model settings.

1 model calls this session
(exit code 0)
(.env restored byte-for-byte: True)
```

`1 model calls this session` with no "served from cache" means the request
really went out. The message put a dead key in the same bucket as a rate
limit and told the user to wait first, which never fixes a bad key. The
handler is now split: `ModelUnavailable` (the model can't be reached at all)
and `RuntimeError` (generate.py still rate limited after its retries) get
different fixed messages. Second trigger, on a query not asked before:

```text
python app.py ask '90s track jacket in size M' --trace
(.env key changed in one character; query: '90s track jacket in size M')
[1] parse_query (local, no model)
      in:  90s track jacket in size M
      out: {"description": "90s track jacket in", "size": "M", "max_price": null}
[2] search_listings (via MCP)
      in:  {"description": "90s track jacket in", "size": "M", "max_price": null}
      out: 1 items: 90s Track Jacket — Navy/White Stripe
      →    branch: not empty, passing lst_004 to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_004 (90s Track Jacket — Navy/White Stripe), wardrobe=10 items
      →    raised ModelUnavailable, stopping; earlier results kept

  Couldn't reach the model, so the outfit suggestion wasn't written. Check that GEMINI_API_KEY in .env is correct and that you're online, then ask again. Waiting won't fix this one.

1 model calls this session
(exit code 0)
(.env restored byte-for-byte: True)
```

The lines in parentheses come from the helper that edited `.env`, ran the
query, and restored the file; it compares SHA-256 before and after and never
prints the key.

## 4. Search server unreachable (added by the MCP move, not one of the three)

`mcp_client.SERVER` pointed at a file that does not exist, for one run only:

```text
python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query (local, no model)
      in:  vintage graphic tee under $30, size M
      out: {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
C:\Users\thegr\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe: can't open file 'C:\\Users\\thegr\\Repos\\RonilBasu-ai201-project2\\mcp_server_missing.py': [Errno 2] No such file or directory
[2] search_listings (via MCP)
      in:  {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
      →    raised MCPError, stopping; earlier results kept

  Could not reach the search tool, which runs as an MCP server (mcp_server.py). Run `python mcp_client.py` to check that the server starts and lists search_listings, then try again.

0 model calls this session
```

The `can't open file` line is the child process's own stderr. Without its own
`except MCPError` branch this would have been reported as a model failure,
because `MCPError` subclasses `RuntimeError`.

## Message check: could a user act on these?

I gave a fresh assistant with no access to the code the three messages exactly
as they first appeared (rows 1, 2 and 3 above, before any change) and the
brief's prompt: "For each one, tell me what I would try next as a user who
can't see the code. If a message leaves me with nothing to try, say so. Don't
rewrite them for me." Its answer, abridged:

> Message 1 gives me clear next steps. It names the three filters that ruled
> everything out, so I would loosen one at a time. [...] That one does its job.
>
> Message 2 doesn't read as an error at all. It looks like a normal result.
> The only clue is the phrase "with an empty wardrobe," and nothing tells me
> that's a problem or what to do about it. [...] So in practice it gives me
> nothing to try.
>
> Message 3 gives me a first step: wait and retry. The fallback is weaker.
> "Unavailable or its request limit was reached" covers two different
> problems, and I can't tell which one I hit, so I don't know whether waiting
> longer will fix it.

Message 1 stayed as it was. Messages 2 and 3 were changed as shown above.
