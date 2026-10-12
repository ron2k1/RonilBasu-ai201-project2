#!/usr/bin/env python3
"""
Score a run_eval.py run against criteria.md.

    python score_run.py                                  newest results/run_*.json
    python score_run.py results/run_2026-10-11_2300_before.json

run_eval.py records what happened and deliberately does not judge it. This is
the judging half: each check_N below is criterion N from criteria.md written
as code. It was committed before the first scored run, so the rules could not
be bent to fit the results.

Criterion 5's size and price rules are literal values copied from the
criterion, not calls into tools.py, so the search is not graded by itself.
Criterion 4's grounding check is a word list; every caption is also read by
hand, and the README says where a reading disagrees with this file.
"""

import json
import re
import sys
from pathlib import Path

import config

TARGETS = {1: 4, 2: 5, 3: 5, 4: 4, 5: 5}
LABELS = {
    1: "Matching query completes all three tools",
    2: "Impossible query stops before the second tool",
    3: "Selected item reaches both later tools unchanged",
    4: "Caption is short, specific, and grounded",
    5: "Search respects the size and price together",
}
EXPECTED_TOOLS = ["search_listings", "suggest_outfit", "create_fit_card"]


def _session(record):
    if record.get("crashed"):
        return None, f"crashed: {record['crashed'][:80]}"
    if not record.get("session"):
        return None, "no session recorded"
    return record["session"], ""


def _tools(session):
    return [call["tool"] for call in session.get("tool_calls", [])]


# ── 1 ───────────────────────────────────────────────────────────────────────

def check_1(record):
    s, why = _session(record)
    if s is None:
        return False, why
    if s.get("error"):
        return False, f"stopped: {s['error'][:90]}"
    if _tools(s) != EXPECTED_TOOLS:
        return False, f"tools were {_tools(s)}"
    if not (s.get("fit_card") or "").strip():
        return False, "fit_card empty"
    return True, "error None, three tools in order, fit card present"


# ── 2 ───────────────────────────────────────────────────────────────────────

def check_2(record):
    s, why = _session(record)
    if s is None:
        return False, why
    if _tools(s) != ["search_listings"]:
        return False, f"tools were {_tools(s)}"
    if s.get("fit_card") is not None:
        return False, "fit_card is not None"
    if not re.search(r"keyword|size|budget", s.get("error") or "", re.I):
        return False, f"error names no change: {s.get('error')!r}"
    return True, "only search_listings, fit_card None, error names keywords/size/budget"


# ── 3 ───────────────────────────────────────────────────────────────────────

def check_3(record):
    s, why = _session(record)
    if s is None:
        return False, why
    if not s.get("search_results"):
        return False, "search returned nothing"
    first = s["search_results"][0]
    if s.get("selected_item") != first:
        return False, "selected_item differs from search_results[0]"
    inputs = {call["tool"]: call["inputs"] for call in s.get("tool_calls", [])}
    for tool in ("suggest_outfit", "create_fit_card"):
        if tool not in inputs:
            return False, f"never reached {tool}"
        if inputs[tool].get("new_item") != first:
            return False, f"{tool} received a different new_item"
    return True, f"{first['id']} identical in search_results[0], selected_item, both new_item inputs"


# ── 4 ───────────────────────────────────────────────────────────────────────

# A naming of the selected item is a noun phrase on the item's own noun
# (criteria.md, criterion 4 revision). Only lst_002 is selected by this query.
ITEM_NOUN = {"lst_002": r"(?<!tank )(?<!on )\b(?:tee|t-?shirt|top)\b(?! of\b)"}
# Pieces that can appear in an outfit drawn from the example wardrobe.
WARDROBE_NOUNS = ["jeans", "trousers", "khakis", "tank", "sweatshirt", "crewneck",
                  "hoodie", "jacket", "sneakers", "boots", "belt", "bag"]
# Claims the selected listing cannot support (lst_002: brand null, condition
# excellent, no material, nothing about shipping or price cuts).
INVENTED = {
    "shipping": r"\bship(?:s|ping|ped)?\b|\bdeliver(?:y|ed|s)?\b",
    "discount": r"\bdiscount\w*|\d+\s?% off\b|\bon sale\b|\bmarked down\b|\bclearance\b|\bcoupon\b|\bpromo\b",
    "condition": r"\bbrand[- ]new\b|\bnew with tags\b|\bnwt\b|\blike[- ]new\b|\bnever worn\b|"
                 r"\bbarely worn\b|\bworn once\b|\bgently (?:used|worn)\b|\bmint\b|\bpristine\b|"
                 r"\bflawless\b|\bperfect condition\b",
    "material": r"\b(?:cotton|polyester|silk|linen|wool|cashmere|rayon|spandex|nylon|satin|velvet|mesh)\b",
    "brand": r"\bbrand(?:ed)?\b|\bdesigner\b|\blevi'?s?\b|\bwrangler\b|\bnike\b|\badidas\b|\bcarhartt\b|"
             r"\bchampion\b|\bzara\b|\bgap\b|\bh&m\b|\bralph lauren\b|\btommy\b|\bguess\b|\bjuicy\b|"
             r"\bbaby phat\b|\bvon dutch\b|\bed hardy\b",
}


def sentence_count(text):
    """Terminal . ! ?; a run of marks is one ending; a decimal point is not."""
    return len(re.findall(r"[.!?]+", re.sub(r"(?<=\d)\.(?=\d)", "", text)))


def caption_checks(card, item, outfit):
    """Every criterion 4 check for one caption, as a dict of measurements."""
    price = f"{item['price']:g}"
    nouns_in_card = {n for n in WARDROBE_NOUNS if re.search(rf"\b{n}\b", card, re.I)}
    nouns_in_outfit = {n for n in WARDROBE_NOUNS if re.search(rf"\b{n}\b", outfit or "", re.I)}
    noun = ITEM_NOUN.get(item["id"])
    return {
        "sentences": sentence_count(card),
        "words": len(card.split()),
        "namings": len(re.findall(noun, card, re.I)) if noun else None,
        "price_mentions": len(re.findall(rf"\$\s?{re.escape(price)}(?:\.0+)?(?!\.?\d)", card)),
        "platform_mentions": len(re.findall(rf"\b{re.escape(item['platform'])}\b", card, re.I)),
        "outfit_details": sorted(nouns_in_card & nouns_in_outfit),
        "invented": sorted(k for k, pattern in INVENTED.items() if re.search(pattern, card, re.I)),
    }


def caption_failures(m):
    fails = []
    if not 2 <= m["sentences"] <= 4:
        fails.append(f"{m['sentences']} sentences")
    if m["words"] > 70:
        fails.append(f"{m['words']} words")
    if m["namings"] != 1:
        fails.append(f"item named {m['namings']}x")
    if m["price_mentions"] != 1:
        fails.append(f"price {m['price_mentions']}x")
    if m["platform_mentions"] != 1:
        fails.append(f"platform {m['platform_mentions']}x")
    if not m["outfit_details"]:
        fails.append("no outfit detail")
    if m["invented"]:
        fails.append("invented " + "/".join(m["invented"]))
    return fails


def check_4(record):
    s, why = _session(record)
    if s is None:
        return False, why
    card = (s.get("fit_card") or "").strip()
    if not card:
        return False, "no fit card"
    item = s.get("selected_item") or {}
    if item.get("id") not in ITEM_NOUN:
        return False, f"unexpected item {item.get('id')}"
    m = caption_checks(card, item, s.get("outfit_suggestion"))
    fails = caption_failures(m)
    summary = (f"{m['sentences']} sent, {m['words']} words, named {m['namings']}x, "
               f"price {m['price_mentions']}x, platform {m['platform_mentions']}x, "
               f"details {m['outfit_details']}")
    return (not fails), ("; ".join(fails) + " | " if fails else "") + summary


# ── 5 ───────────────────────────────────────────────────────────────────────

M_SIZES = {"M", "S/M", "M/L"}
C5_CASES = {
    "butterfly size M under $18": (lambda size: size in M_SIZES, 18.0, "lst_002"),
    "flannel size XL under $22": (lambda size: re.search(r"(?<![A-Za-z])XL(?![A-Za-z])", size), 22.0, "lst_003"),
    "platform sneakers size 8 under $48": (lambda size: re.fullmatch(r"(?:US )?8", size), 48.0, "lst_019"),
    "jeans size W30 L30 under $38": (lambda size: {"W30", "L30"} <= set(size.split()), 38.0, "lst_001"),
    "track jacket size M under $45": (lambda size: size in M_SIZES, 45.0, "lst_004"),
}


def check_5(record):
    s, why = _session(record)
    if s is None:
        return False, why
    case = C5_CASES.get(record.get("query"))
    if case is None:
        return False, f"no criterion 5 case for {record.get('query')!r}"
    size_ok, ceiling, expected = case
    results = s.get("search_results") or []
    if not results:
        return False, "empty result"
    bad = [r["id"] for r in results if r["price"] > ceiling or not size_ok(r["size"])]
    if bad:
        return False, f"out of size/price: {bad}"
    ids = [r["id"] for r in results]
    if expected not in ids:
        return False, f"{expected} missing from {ids}"
    return True, f"{len(results)} result(s) {ids}, all within size and ${ceiling:g}"


CHECKS = {1: check_1, 2: check_2, 3: check_3, 4: check_4, 5: check_5}


# ── report ──────────────────────────────────────────────────────────────────

def score(raw):
    """Return {criterion: [(passed, reason), ...]} for every numbered scenario."""
    scored = {}
    for row in raw["rows"]:
        number = row["scenario"].get("criterion")
        if number in CHECKS:
            scored[number] = [CHECKS[number](record) for record in row["tries"]]
    return scored


def verdict(number, results):
    passes = sum(ok for ok, _ in results)
    met = passes >= TARGETS[number] and len(results) >= 5
    return f"{'MET' if met else 'MISSED'} ({passes}/{len(results)})"


def report(raw, source):
    scored = score(raw)
    n = raw["tries"]
    lines = [
        f"# Scored run — {raw.get('label') or 'unlabeled'}",
        "",
        f"- Source: `{source}` (written by `run_eval.py::write_report`)",
        f"- Scored by: `score_run.py::score`, rules committed before the first run",
        f"- Model: {raw.get('model')}, temperature {raw.get('temperature')}, "
        f"{n} tries per scenario, cache off",
        "",
        "| Criterion | Target | " + " | ".join(f"Try {i}" for i in range(1, n + 1)) + " | Verdict |",
        "|---|---|" + "|".join(["---"] * n) + "|---|",
    ]
    for number in sorted(scored):
        cells = " | ".join("PASS" if ok else "FAIL" for ok, _ in scored[number])
        lines.append(f"| {number}. {LABELS[number]} | {TARGETS[number]} of 5 | {cells} | "
                     f"{verdict(number, scored[number])} |")
    lines += ["", "## Why each try passed or failed", ""]
    for number in sorted(scored):
        lines += [f"**{number}. {LABELS[number]}**", ""]
        lines += [f"- Try {i}: {'PASS' if ok else 'FAIL'} — {why}"
                  for i, (ok, why) in enumerate(scored[number], 1)]
        lines.append("")
    for row in raw["rows"]:
        if row["scenario"].get("criterion") is None:
            lines += [f"**Diagnostic, not scored: {row['scenario']['name']}**", ""]
            for i, record in enumerate(row["tries"], 1):
                s = record.get("session") or {}
                state = record.get("crashed") or s.get("error") or "completed"
                lines.append(f"- Try {i}: {state[:90]}; notice "
                             f"{'shown' if s.get('notice') else 'missing'}")
            lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        runs = sorted(config.RESULTS_DIR.glob("run_*.json"))
        if not runs:
            sys.exit("No results/run_*.json yet. Run `python run_eval.py --label before` first.")
        path = runs[-1]
    raw = json.loads(path.read_text(encoding="utf-8"))
    text = report(raw, path.as_posix())
    out = path.with_name(path.stem.replace("run_", "score_", 1) + ".md")
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nWrote {out.relative_to(config.ROOT) if out.is_absolute() else out}")


if __name__ == "__main__":
    main()
