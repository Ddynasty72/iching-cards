#!/usr/bin/env python3
"""
I Ching - terminal version
==========================
A single-file, no-dependency Python program that casts the traditional
three-coin I Ching in a terminal, for inner-work reading in the Taoist
frame of Liu Yiming's commentary (Thomas Cleary's translation,
"The Taoist I Ching").

The program prints no I Ching or commentary text. It casts, draws the
hexagrams, and tells you exactly which passages to open in your own copy.

RUNNING IT
----------
1. Save this file as iching.py in any folder.
2. Open a terminal in that folder (in VS Code: Terminal > New Terminal,
   or Ctrl+` on Windows).
3. Run:  python iching.py
   (use python3 on Mac / Linux if `python` is not found; Python 3.8+)

OPTIONS
-------
  python iching.py --help
  python iching.py -i                 toss one line at a time (Enter)
  python iching.py -q "my question"   record a question with the cast
  python iching.py --rules zhuxi      narrow the reading with Zhu Xi's rules
  python iching.py --primary 41       keep Hexagram 41; only the moving
                                      lines are cast (NOT a true cast)
  python iching.py --seed 7           demo only: fixed result, never use
                                      for a real cast
  python iching.py --save cast.json   save the cast as JSON

HOW A CAST WORKS
----------------
Six lines, tossed bottom (line 1) to top (line 6).
Each line: toss 3 coins. Heads = 3, tails = 2.
  6 = old yin    - broken line, MOVING -> becomes yang
  7 = young yang - solid line, stable
  8 = young yin  - broken line, stable
  9 = old yang   - solid line, MOVING -> becomes yin
Each line moves with probability 1 in 4. (The three-coin method gives old
yin and old yang equal chances; the yarrow-stalk method does not.)
Randomness comes from the operating system (secrets module), not from the
date or time.

THE FRAME
---------
A moving line is where yin or yang has reached its extreme and turns into
its opposite. In the frame this program uses, read it as a correction of a
false attitude at its extreme, not as a prediction. True yin and yang
complement and include one another; false yang is impetuosity,
aggression, stubbornness; false yin is quietism, vacillation, dependency.
(This is a summary in the program author's words, not a quotation.)

READING RULES  (--rules)
------------------------
liu (default)
    Every moving line is kept. Read the primary hexagram, then each moving
    line from bottom to top, then the relating hexagram. Liu Yiming gives
    no casting procedure of his own, so this is a convention: in his frame
    each line is a diagnostic, so none is set aside. Wilhelm's method is
    close to this.
zhuxi
    Zhu Xi's scheme (Introduction to the Study of the Classic of Change,
    1186), which narrows the passages by the number of moving lines:
      0 moving - the primary hexagram's Judgment.
      1 moving - that line of the primary hexagram is the key.
      2 moving - both lines of the primary hexagram; the upper leads.
      3 moving - both Judgments; the primary leads if line 1 moved,
                 otherwise the relating hexagram leads.
      4 moving - the two unmoved lines in the relating hexagram; the
                 lower leads.
      5 moving - the one unmoved line in the relating hexagram.
      6 moving - the relating hexagram's Judgment; but for Hexagrams 1
                 and 2 the extra "all lines moving" passage is used.

Line labels ("Nine at the beginning", "Six in the third place") follow
Wilhelm's wording and are set in POSITIONS below; change them there if
your copy words them differently.
"""

import argparse
import json
import random
import secrets
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Trigrams: bit patterns, bottom line -> top line. 1 = yang, 0 = yin.
# ---------------------------------------------------------------------------
TRIGRAMS = {
    "Qian": (1, 1, 1),  # Heaven
    "Kun": (0, 0, 0),   # Earth
    "Zhen": (1, 0, 0),  # Thunder
    "Kan": (0, 1, 0),   # Water
    "Gen": (0, 0, 1),   # Mountain
    "Xun": (0, 1, 1),   # Wind
    "Li": (1, 0, 1),    # Fire
    "Dui": (1, 1, 0),   # Lake
}

TRIGRAM_NAMES = {
    "Qian": ("Heaven", "the Creative"),
    "Kun": ("Earth", "the Receptive"),
    "Zhen": ("Thunder", "the Arousing"),
    "Kan": ("Water", "the Abysmal"),
    "Gen": ("Mountain", "Keeping Still"),
    "Xun": ("Wind", "the Gentle"),
    "Li": ("Fire", "the Clinging"),
    "Dui": ("Lake", "the Joyous"),
}

# ---------------------------------------------------------------------------
# Hexagrams in King Wen order: (number, name, upper trigram, lower trigram).
# EDIT THE NAMES HERE (second item of each entry) to match your copy.
# Leave the numbers and trigrams alone.
# ---------------------------------------------------------------------------
HEXAGRAMS = [
    (1, "Creative", "Qian", "Qian"),
    (2, "Receptive", "Kun", "Kun"),
    (3, "Difficulty at the Beginning", "Kan", "Zhen"),
    (4, "Youthful Folly", "Gen", "Kan"),
    (5, "Waiting", "Kan", "Qian"),
    (6, "Conflict", "Qian", "Kan"),
    (7, "Army", "Kun", "Kan"),
    (8, "Holding Together", "Kan", "Kun"),
    (9, "Small Taming", "Xun", "Qian"),
    (10, "Treading", "Qian", "Dui"),
    (11, "Peace", "Kun", "Qian"),
    (12, "Standstill", "Qian", "Kun"),
    (13, "Fellowship", "Qian", "Li"),
    (14, "Great Possession", "Li", "Qian"),
    (15, "Modesty", "Kun", "Gen"),
    (16, "Enthusiasm", "Zhen", "Kun"),
    (17, "Following", "Dui", "Zhen"),
    (18, "Work on the Decayed", "Gen", "Xun"),
    (19, "Approach", "Kun", "Dui"),
    (20, "Contemplation", "Xun", "Kun"),
    (21, "Biting Through", "Li", "Zhen"),
    (22, "Grace", "Gen", "Li"),
    (23, "Splitting Apart", "Gen", "Kun"),
    (24, "Return", "Kun", "Zhen"),
    (25, "Innocence", "Qian", "Zhen"),
    (26, "Great Taming", "Gen", "Qian"),
    (27, "Nourishment", "Gen", "Zhen"),
    (28, "Great Exceeding", "Dui", "Xun"),
    (29, "Abysmal Water", "Kan", "Kan"),
    (30, "Clinging Fire", "Li", "Li"),
    (31, "Influence", "Dui", "Gen"),
    (32, "Duration", "Zhen", "Xun"),
    (33, "Retreat", "Qian", "Gen"),
    (34, "Great Power", "Zhen", "Qian"),
    (35, "Progress", "Li", "Kun"),
    (36, "Darkening of the Light", "Kun", "Li"),
    (37, "Family", "Xun", "Li"),
    (38, "Opposition", "Li", "Dui"),
    (39, "Obstruction", "Kan", "Gen"),
    (40, "Deliverance", "Zhen", "Kan"),
    (41, "Decrease", "Gen", "Dui"),
    (42, "Increase", "Xun", "Zhen"),
    (43, "Breakthrough", "Dui", "Qian"),
    (44, "Coming to Meet", "Qian", "Xun"),
    (45, "Gathering", "Dui", "Kun"),
    (46, "Pushing Upward", "Kun", "Xun"),
    (47, "Oppression", "Dui", "Kan"),
    (48, "Well", "Kan", "Xun"),
    (49, "Revolution", "Dui", "Li"),
    (50, "Cauldron", "Li", "Xun"),
    (51, "Arousing Thunder", "Zhen", "Zhen"),
    (52, "Keeping Still Mountain", "Gen", "Gen"),
    (53, "Development", "Xun", "Gen"),
    (54, "Marrying Maiden", "Zhen", "Dui"),
    (55, "Abundance", "Zhen", "Li"),
    (56, "Wanderer", "Li", "Gen"),
    (57, "Gentle Wind", "Xun", "Xun"),
    (58, "Joyous Lake", "Dui", "Dui"),
    (59, "Dispersion", "Xun", "Kan"),
    (60, "Limitation", "Kan", "Dui"),
    (61, "Inner Truth", "Xun", "Dui"),
    (62, "Small Exceeding", "Zhen", "Gen"),
    (63, "After Completion", "Kan", "Li"),
    (64, "Before Completion", "Li", "Kan"),
]

# Line positions, as worded in line labels. Edit to match your copy.
POSITIONS = {
    1: "at the beginning",
    2: "in the second place",
    3: "in the third place",
    4: "in the fourth place",
    5: "in the fifth place",
    6: "at the top",
}

# Hexagrams 1 and 2 carry an extra passage for "all lines moving".
ALL_MOVING_TEXT = {
    1: "the extra passage that follows the line texts, for all lines "
       "moving (all nines)",
    2: "the extra passage that follows the line texts, for all lines "
       "moving (all sixes)",
}

# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
HEX_BY_NUM = {num: (name, upper, lower) for num, name, upper, lower in HEXAGRAMS}
BY_LINES = {
    TRIGRAMS[lower] + TRIGRAMS[upper]: num
    for num, _name, upper, lower in HEXAGRAMS
}
# Catches a bad edit to the table above.
assert len(HEX_BY_NUM) == 64 and len(BY_LINES) == 64, "hexagram table is broken"


def lines_for(number):
    """Line pattern bottom -> top for a hexagram number (1=yang, 0=yin)."""
    _name, upper, lower = HEX_BY_NUM[number]
    return TRIGRAMS[lower] + TRIGRAMS[upper]


def describe(number):
    name, upper, lower = HEX_BY_NUM[number]
    up_name, up_nature = TRIGRAM_NAMES[upper]
    lo_name, lo_nature = TRIGRAM_NAMES[lower]
    return {
        "number": number,
        "name": name,
        "upper": f"{up_name} ({up_nature})",
        "lower": f"{lo_name} ({lo_nature})",
        "title": f"{up_name} over {lo_name}",
        "lines_bottom_to_top": list(lines_for(number)),
    }


def line_label(line_no, is_yang):
    """Book-style label, e.g. 'Nine at the beginning', 'Six in the third place'."""
    return f"{'Nine' if is_yang else 'Six'} {POSITIONS[line_no]}"


def hx(number):
    return f"Hexagram {number} ({HEX_BY_NUM[number][0]})"


# ---------------------------------------------------------------------------
# Casting
# ---------------------------------------------------------------------------
def toss(rng):
    """Three coins, heads=3, tails=2. rng() returns 0 or 1 per coin."""
    coins = [rng() for _ in range(3)]
    return sum(3 if c else 2 for c in coins), coins


def result_from_values(values):
    """Build the full result from six line values (each 6, 7, 8 or 9)."""
    moving = [i + 1 for i, v in enumerate(values) if v in (6, 9)]
    primary_lines = [1 if v in (7, 9) else 0 for v in values]
    relating_lines = [
        (1 - b) if (i + 1) in moving else b for i, b in enumerate(primary_lines)
    ]
    primary = BY_LINES[tuple(primary_lines)]
    relating = BY_LINES[tuple(relating_lines)] if moving else None
    return {
        "values": list(values),
        "moving": moving,
        "primary_lines": primary_lines,
        "relating_lines": relating_lines,
        "primary": primary,
        "relating": relating,
    }


def cast(rng, primary=None, interactive=False):
    """Toss six lines. With `primary`, keep that hexagram's pattern and let
    the coins decide only which lines move."""
    base = lines_for(primary) if primary is not None else None
    values = []
    for line_no in range(1, 7):
        if interactive:
            input(f"  Line {line_no} - press Enter to toss three coins...")
        total, coins = toss(rng)
        is_moving = total in (6, 9)
        if base is not None:
            yang = base[line_no - 1] == 1
            total = (9 if yang else 6) if is_moving else (7 if yang else 8)
        values.append(total)
        if interactive:
            faces = " ".join("H" if c else "T" for c in coins)
            state = "MOVING" if is_moving else "stable"
            if base is None:
                print(f"    {faces} = {total}  {state}")
            else:
                print(f"    {faces}  {state}")
    return result_from_values(values)


# ---------------------------------------------------------------------------
# Where to read
# ---------------------------------------------------------------------------
def reading_plan(rules, res):
    """Return (steps, note): which passages to open, in order."""
    p, r = res["primary"], res["relating"]
    moving = res["moving"]
    pl, rl = res["primary_lines"], res["relating_lines"]
    n = len(moving)

    def plabel(k):
        return line_label(k, pl[k - 1] == 1)

    def rlabel(k):
        return line_label(k, rl[k - 1] == 1)

    if rules == "liu":
        if n == 0:
            return ([f"{hx(p)}: read it whole. Nothing is moving."],
                    "Stable cast: no tipping point, so the primary hexagram "
                    "stands alone.")
        steps = [f"{hx(p)}: the situation as it stands."]
        for k in moving:
            steps.append(f"{hx(p)}, {plabel(k)} (line {k} moves).")
        if n == 6 and p in ALL_MOVING_TEXT:
            steps.append(f"{hx(p)}: {ALL_MOVING_TEXT[p]}.")
        steps.append(f"{hx(r)}: where the correction tends.")
        return (steps,
                "Every moving line is kept: each is a false attitude at its "
                "extreme, so none is set aside.")

    # Zhu Xi's rules
    unmoved = [k for k in range(1, 7) if k not in moving]
    if n == 0:
        return ([f"{hx(p)}: read the Judgment."],
                "Stable: no moving lines. Read the primary hexagram only.")
    if n == 1:
        k = moving[0]
        return ([f"{hx(p)}, {plabel(k)}: the key."],
                f"One moving line: that line is the key; {hx(r)} is the "
                "direction it tends to.")
    if n == 2:
        lo, up = moving
        return ([f"{hx(p)}, {plabel(up)} (leads).",
                 f"{hx(p)}, {plabel(lo)}."],
                "Two moving lines: read both; the upper carries the weight.")
    if n == 3:
        if 1 in moving:
            lead, other = p, r
            why = "the primary leads because line 1 moved"
        else:
            lead, other = r, p
            why = "the relating hexagram leads because line 1 did not move"
        return ([f"{hx(lead)}: Judgment (leads).",
                 f"{hx(other)}: Judgment."],
                f"Three moving lines: read both Judgments; {why}.")
    if n == 4:
        lo, up = unmoved
        return ([f"{hx(r)}, {rlabel(lo)} (leads).",
                 f"{hx(r)}, {rlabel(up)}."],
                "Four moving lines: read the two unmoved lines in the "
                "relating hexagram; the lower leads.")
    if n == 5:
        k = unmoved[0]
        return ([f"{hx(r)}, {rlabel(k)}."],
                "Five moving lines: read the one unmoved line in the "
                "relating hexagram.")
    # n == 6
    if p in ALL_MOVING_TEXT:
        return ([f"{hx(p)}: {ALL_MOVING_TEXT[p]}."],
                "Six moving lines on Hexagram 1 or 2: Zhu Xi uses the extra "
                "passage in place of the relating Judgment.")
    return ([f"{hx(r)}: Judgment."],
            "Six moving lines: read the relating hexagram's Judgment.")


# ---------------------------------------------------------------------------
# Terminal display
# ---------------------------------------------------------------------------
SOLID = "\u2588" * 8              # ████████
BROKEN = "\u2588" * 3 + "  " + "\u2588" * 3   # ███  ███ (same width)


def bar(bit):
    return SOLID if bit else BROKEN


def draw_cast(res):
    """Primary hexagram, and the relating one beside it if lines move.
    Top line (6) first. o = old yang (9), x = old yin (6)."""
    values, moving = res["values"], res["moving"]
    pl, rl = res["primary_lines"], res["relating_lines"]
    has_rel = res["relating"] is not None
    if has_rel:
        head = "     " + "PRIMARY".ljust(len(SOLID) + 9) + "TENDING TO"
    else:
        head = "     PRIMARY"
    rows = [head]
    for i in range(5, -1, -1):
        no = i + 1
        mark = {9: "o", 6: "x"}.get(values[i], " ")
        row = f"  {no}  {bar(pl[i])}"
        if has_rel:
            arrow = "->" if no in moving else "  "
            row += f"  {mark}  {arrow}  {bar(rl[i])}"
        rows.append(row.rstrip())
    return "\n".join(rows)


def print_hexagram(label, number):
    info = describe(number)
    print(f"{label}: Hexagram {info['number']} - {info['name']}")
    print(f"    {info['title']}  (upper: {info['upper']}; "
          f"lower: {info['lower']})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(args):
    if args.seed is not None:
        print("DEMO MODE: fixed seed - not a real cast.\n")
        demo_rng = random.Random(args.seed)

        def coin():
            return demo_rng.randint(0, 1)
    else:
        def coin():
            return secrets.randbelow(2)  # OS entropy

    print("I Ching - three coins, six lines, bottom to top")
    print("Heads = 3, tails = 2. 6 and 9 move; 7 and 8 are stable.\n")
    if args.primary is not None:
        print(f"Note: Hexagram {args.primary} was chosen by you (--primary). "
              "Only the moving lines are cast; this is not a true cast.\n")

    question = args.question
    if args.interactive and question is None:
        question = input("Hold your question in mind. Type it, or press "
                         "Enter to skip: ").strip() or None
        print()
    if question:
        print(f"Question: {question}\n")

    res = cast(coin, primary=args.primary, interactive=args.interactive)
    p, r, moving = res["primary"], res["relating"], res["moving"]

    if args.interactive:
        print()
    print("Casts, bottom to top (line 1 to line 6):",
          " ".join(str(v) for v in res["values"]))
    print("Moving lines:", ", ".join(str(m) for m in moving)
          if moving else "none")
    print()
    print(draw_cast(res))
    if moving:
        print("\n  o = old yang (9), x = old yin (6): moving lines, each "
              "turning into its opposite.")
    print()
    print_hexagram("PRIMARY", p)
    if r is not None:
        print_hexagram("TENDING TO", r)

    steps, note = reading_plan(args.rules, res)
    title = ("Liu mode: every moving line kept" if args.rules == "liu"
             else "Zhu Xi's rules")
    print(f"\nWHERE TO READ  ({title})")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print(f"  {note}")

    print("\nIn Liu Yiming's frame, a moving line is a tipping point - a false")
    print("attitude at its extreme, correcting itself - not a prediction.")
    print("Ask what in yourself it is correcting.")

    if args.save:
        result = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "question": question,
            "demo_seed": args.seed,
            "primary_chosen_by_user": args.primary is not None,
            "rules": args.rules,
            "casts_bottom_to_top": res["values"],
            "moving_lines": moving,
            "primary": describe(p),
            "relating": describe(r) if r else None,
            "where_to_read": steps,
        }
        try:
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            print(f"\nCould not save to {args.save}: {exc}")
            return 1
        print(f"\nSaved to {args.save}")
    return 0


def main(argv=None):
    # Keep block characters and dashes safe on Windows consoles and pipes.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="iching.py",
        description="I Ching: three-coin cast in the terminal.",
        epilog="Examples:  python iching.py   |   python iching.py -i -q "
               "\"What needs correcting?\" --save cast.json",
    )
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="toss one line at a time, pressing Enter "
                             "(also asks for your question)")
    parser.add_argument("-q", "--question", default=None,
                        help="record your question with the cast")
    parser.add_argument("--rules", choices=("liu", "zhuxi"), default="liu",
                        help="liu (default) keeps every moving line; zhuxi "
                             "narrows the passages by Zhu Xi's rules")
    parser.add_argument("--primary", type=int, default=None, metavar="N",
                        help="keep hexagram N's pattern (1-64); coins decide "
                             "only which lines move. Not a true cast")
    parser.add_argument("--seed", type=int, default=None,
                        help="demo only: fixed result, never for a real cast")
    parser.add_argument("--save", default=None, metavar="FILE",
                        help="save the cast as JSON, e.g. cast.json")
    args = parser.parse_args(argv)
    if args.primary is not None and not 1 <= args.primary <= 64:
        parser.error("--primary must be a hexagram number 1-64")

    try:
        return run(args)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
