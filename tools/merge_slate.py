#!/usr/bin/env python3
"""Merge a freshly pulled slate into the existing one, preserving line-movement history.

Run this on EVERY refresh instead of overwriting slate.json, or the opening
lines are lost and movement history resets.

    python3 tools/merge_slate.py new_slate.json            # writes slate.json
    python3 tools/merge_slate.py new_slate.json --date 2026-09-12

Rules
  - Games are matched on (league, away, home).
  - A game already on the board keeps its existing sit block (and therefore its
    open) and gains one new snapshot entry [date, spread, total] when either
    number has changed since the last snapshot.
  - A game not previously on the board starts a fresh history: this pull is its open.
  - Games that dropped out of the new pull are kept if they have already kicked
    off (line-lock rule), otherwise dropped.
"""
import json, sys, argparse, datetime

SPREAD, TOTAL, KO, SIT = 7, 8, 6, 21

def key(a): return (a[0], a[1], a[2])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new_slate")
    ap.add_argument("--current", default="slate.json")
    ap.add_argument("--out", default="slate.json")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()

    cur = json.load(open(args.current))
    new = json.load(open(args.new_slate))
    old = {key(a): a for a in cur["g"]}

    added = moved = carried = 0
    out = []
    for a in new["g"]:
        while len(a) < SIT: a.append(None)
        prev = old.get(key(a))
        if prev and len(prev) > SIT and isinstance(prev[SIT], dict):
            sit = dict(prev[SIT])
            mv = list(sit.get("mv") or [])
            if not mv or mv[-1][1] != a[SPREAD] or mv[-1][2] != a[TOTAL]:
                mv.append([args.date, a[SPREAD], a[TOTAL]])
                moved += 1
            sit["mv"] = mv
            carried += 1
        else:
            sit = {"mv": [[args.date, a[SPREAD], a[TOTAL]]]}
            added += 1
        if len(a) == SIT: a.append(sit)
        else: a[SIT] = sit
        out.append(a)

    # keep kicked-off games so the tracker/lock still sees them
    seen = {key(a) for a in out}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for k, a in old.items():
        if k in seen: continue
        if a[KO] and a[KO] <= now:
            out.append(a)

    new["g"] = out
    new["v"] = 2
    new.setdefault("sit", {})["note"] = cur.get("sit", {}).get(
        "note", "index 21 = situational block; mv = [[date,spread,total],...] oldest first.")
    json.dump(new, open(args.out, "w"), separators=(",", ":"))
    print(f"{len(out)} games -> {args.out}  (new {added}, carried {carried}, moved {moved})")

if __name__ == "__main__":
    main()
