#!/usr/bin/env python3
"""
DSA Pattern Sheet Manager
─────────────────────────
Add or remove problems from Pattern_Sheet.html without touching any
other part of the file.  Run from the same directory as the HTML file:

    python manage_patterns.py
    python manage_patterns.py --file path/to/Pattern_Sheet.html
"""

import re
import json
import sys
import os
import argparse
import textwrap
from copy import deepcopy

# ─── Colour pool (accent hex values covering the full hue wheel) ──────────────
# bg and border are derived automatically; add more accents here if needed.
import colorsys as _cs, random as _random

_ACCENT_POOL = [
    "#6c5fc7","#1a8a6b","#c47d1a","#b84c28","#a83860",
    "#2264b8","#437a1e","#5a5855","#7c5c1e","#c0392b",
    "#8e44ad","#16a085","#d35400","#2980b9","#27ae60",
    "#f39c12","#7f8c8d","#1abc9c","#9b59b6","#e74c3c",
    "#3d6b99","#a04000","#117a65","#6c3483","#1f618d",
    "#b7950b","#784212","#2e4057","#5d6d7e","#196f3d",
    "#922b21","#1a5276","#0e6655","#784212","#4a235a",
]

def _hex_to_hls(h: str):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    return _cs.rgb_to_hls(r, g, b)          # (hue, lightness, saturation)

def _hls_to_hex(h, l, s) -> str:
    r, g, b = _cs.hls_to_rgb(h, max(0,min(1,l)), max(0,min(1,s)))
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def _derive_palette(accent: str) -> dict:
    """Given an accent hex, compute a harmonious light bg and border."""
    hue, _, sat = _hex_to_hls(accent)
    bg     = _hls_to_hex(hue, 0.96, min(sat, 0.60))
    border = _hls_to_hex(hue, 0.84, min(sat, 0.55))
    return {"color": accent, "bg": bg, "border": border}

def _used_colors(patterns: list) -> set:
    """Collect every accent colour already present in the sheet."""
    used = set()
    for p in patterns:
        if p.get("color"):
            used.add(p["color"].lower())
        if p.get("isGroup"):
            for c in p.get("children", []):
                if c.get("color"):
                    used.add(c["color"].lower())
    return used

def pick_color(patterns: list) -> dict:
    """
    Pick a random accent colour not yet used in the sheet,
    then derive its bg and border automatically.
    """
    used      = _used_colors(patterns)
    available = [c for c in _ACCENT_POOL if c.lower() not in used]
    if not available:
        # All pool colours exhausted — generate a genuinely new hue
        used_hues = {_hex_to_hls(c)[0] for c in used if c.startswith("#") and len(c)==7}
        for _ in range(200):
            h = _random.random()
            if all(abs(h - uh) > 0.05 for uh in used_hues):
                sat = _random.uniform(0.45, 0.70)
                lit = _random.uniform(0.28, 0.45)
                accent = _hls_to_hex(h, lit, sat)
                available = [accent]
                break
        else:
            available = [_random.choice(_ACCENT_POOL)]   # last resort

    accent = _random.choice(available)
    palette = _derive_palette(accent)
    print(f"  🎨  Auto-assigned colour: {accent}")
    return palette

PLATFORMS = {"lc": "LeetCode", "gfg": "GeeksForGeeks", "cn": "Coding Ninjas / Naukri"}

# ─── Extraction helpers ───────────────────────────────────────────────────────

def load_html(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def save_html(filepath: str, content: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def extract_patterns_block(html: str):
    """
    Returns (full_match_str, list_str, start_of_list, end_of_list)
    where start/end index the '[…]' portion inside html.
    """
    pattern = re.compile(r'const patterns\s*=\s*(\[)', re.DOTALL)
    m = pattern.search(html)
    if not m:
        raise ValueError("Could not locate 'const patterns = [' in the HTML file.")

    bracket_start = m.start(1)
    depth = 0
    for i in range(bracket_start, len(html)):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                bracket_end = i + 1          # exclusive
                return html[bracket_start:bracket_end], bracket_start, bracket_end
    raise ValueError("Unbalanced brackets in patterns array.")

def js_array_to_python(js_str: str):
    """
    Parse a JavaScript array literal -> Python object.

    Strategy:
      1. Try Node.js (handles everything natively).
         Looks for 'node' and 'nodejs' -- covers Ubuntu/Debian where the
         binary is called 'nodejs'.
      2. Pure-Python fallback for machines with no Node at all.
    """
    import subprocess, shutil, tempfile

    node_bin = shutil.which("node") or shutil.which("nodejs")
    if node_bin:
        script = "const d=" + js_str + "; process.stdout.write(JSON.stringify(d));"
        tmp = tempfile.NamedTemporaryFile(
            suffix=".js", mode="w", delete=False, encoding="utf-8"
        )
        tmp.write(script)
        tmp.close()
        try:
            result = subprocess.run(
                [node_bin, tmp.name],
                capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            raise ValueError("Node.js evaluation failed:\n" + result.stderr.strip())
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    # -- Pure-Python fallback (no Node available) ------------------------------
    # Walk character-by-character so we never accidentally transform characters
    # that are inside string literals (e.g. special unicode, colons in URLs).
    OUT = []
    i   = 0
    s   = js_str

    while i < len(s):
        ch = s[i]

        # single-line comment
        if ch == '/' and i + 1 < len(s) and s[i + 1] == '/':
            while i < len(s) and s[i] != '\n':
                i += 1
            continue

        # single-quoted string -> double-quoted
        if ch == "'":
            OUT.append('"')
            i += 1
            while i < len(s):
                c = s[i]
                if c == '\\' and i + 1 < len(s):
                    nc = s[i + 1]
                    if nc == "'":
                        OUT.append("'")
                        i += 2
                    else:
                        OUT.append(c)
                        OUT.append(nc)
                        i += 2
                elif c == '"':
                    OUT.append('\\"')
                    i += 1
                elif c == "'":
                    OUT.append('"')
                    i += 1
                    break
                else:
                    OUT.append(c)
                    i += 1
            continue

        # double-quoted string -> copy verbatim
        if ch == '"':
            OUT.append(ch)
            i += 1
            while i < len(s):
                c = s[i]
                OUT.append(c)
                if c == '\\' and i + 1 < len(s):
                    OUT.append(s[i + 1])
                    i += 2
                    continue
                if c == '"':
                    i += 1
                    break
                i += 1
            continue

        OUT.append(ch)
        i += 1

    cleaned = ''.join(OUT)
    # Quote bare object keys
    cleaned = re.sub(r'(?<!["\w])([A-Za-z_$][A-Za-z0-9_$]*)\s*:', r'"\1":', cleaned)
    # Remove trailing commas
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    return json.loads(cleaned)


def python_to_js(data) -> str:
    """Serialise back to a JS array literal (JSON-compatible subset)."""
    return json.dumps(data, indent=2, ensure_ascii=False)

def rebuild_html(html: str, new_patterns: list) -> str:
    _, start, end = extract_patterns_block(html)
    new_block = python_to_js(new_patterns)
    return html[:start] + new_block + html[end:]

# ─── Display helpers ──────────────────────────────────────────────────────────

def hr(char="─", width=60):
    print(char * width)

def section(title: str):
    hr()
    print(f"  {title}")
    hr()

def numbered_list(items, formatter=str):
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {formatter(item)}")

def pick(prompt: str, lo: int, hi: int) -> int:
    while True:
        raw = input(f"\n{prompt} [{lo}–{hi}]: ").strip()
        if raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        print(f"       ✗  Please enter a number between {lo} and {hi}.")

def confirm(prompt: str) -> bool:
    return input(f"\n{prompt} [y/N]: ").strip().lower() == "y"

# ─── Input helpers ────────────────────────────────────────────────────────────

def ask(prompt: str, required=True, default=None) -> str:
    hint = f" (default: {default})" if default else (" (optional, press Enter to skip)" if not required else "")
    while True:
        val = input(f"  {prompt}{hint}: ").strip()
        if val:
            return val
        if default is not None:
            return default
        if not required:
            return ""
        print("       ✗  This field is required.")

def ask_lc_number() -> (int | None):
    while True:
        raw = ask("LeetCode problem number", required=False)
        if raw == "":
            return None
        if raw.isdigit():
            return int(raw)
        print("       ✗  Enter digits only, or press Enter to skip.")

def ask_platform() -> str:
    print("\n  Platform:")
    for k, v in PLATFORMS.items():
        print(f"    • {k}  →  {v}")
    while True:
        val = input("  Your choice (lc / gfg / cn): ").strip().lower()
        if val in PLATFORMS:
            return val
        print("       ✗  Enter one of: lc, gfg, cn")



def slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# ─── Flat problem list ────────────────────────────────────────────────────────

def flat_problems(patterns: list) -> list:
    """
    Returns a list of dicts with extra keys for display / lookup:
        _pattern_label, _pattern_path  e.g. ("array-patterns", "prefix-sum") or ("two-pointers",)
        _prob_index     index inside the problems list
    """
    result = []
    for p in patterns:
        if p.get("isGroup"):
            for child in p.get("children", []):
                for idx, prob in enumerate(child.get("problems", [])):
                    result.append({
                        **prob,
                        "_label":   f"{p['name']} → {child['name']}",
                        "_path":    (p["id"], child["id"]),
                        "_idx":     idx,
                    })
        else:
            for idx, prob in enumerate(p.get("problems", [])):
                result.append({
                    **prob,
                    "_label":   p["name"],
                    "_path":    (p["id"],),
                    "_idx":     idx,
                })
    return result

def fmt_prob(prob: dict) -> str:
    lc = f"  LC#{prob['lc']}" if prob.get("lc") else ""
    return f"{prob['title']}{lc}  [{prob['_label']}]"

# ─── Core operations ──────────────────────────────────────────────────────────

def list_problems(patterns: list):
    section("ALL PROBLEMS")
    all_probs = flat_problems(patterns)
    if not all_probs:
        print("  (no problems yet)")
        return
    numbered_list(all_probs, fmt_prob)
    print(f"\n  Total: {len(all_probs)} problems")

# ── ADD ───────────────────────────────────────────────────────────────────────

def collect_problem_fields() -> dict:
    """Ask the user for the fields of a single problem entry."""
    print()
    title    = ask("Problem title")
    lc_num   = ask_lc_number()
    platform = ask_platform()
    url      = ask("Problem URL")
    return {"title": title, "lc": lc_num, "platform": platform, "url": url}

def add_to_existing_pattern(patterns: list) -> list:
    """Add a problem to an existing (non-group) pattern."""
    flat = [p for p in patterns if not p.get("isGroup")]
    if not flat:
        print("  No regular patterns found.")
        return patterns

    print("\n  Existing patterns:")
    numbered_list(flat, lambda p: f"{p['name']}  ({len(p['problems'])} problems)")
    choice = pick("Select pattern", 1, len(flat))
    target = flat[choice - 1]

    prob = collect_problem_fields()

    # Mutate the real patterns list
    new_patterns = deepcopy(patterns)
    for p in new_patterns:
        if p["id"] == target["id"]:
            p["problems"].append(prob)
            break

    print(f"\n  ✓  Added «{prob['title']}» to pattern «{target['name']}».")
    return new_patterns

def add_new_pattern(patterns: list) -> list:
    """Create a brand-new top-level pattern with one problem."""
    section("NEW PATTERN DETAILS")
    name   = ask("Pattern name  (e.g. Backtracking)")
    pat_id = slug(name)
    colors = pick_color(patterns)

    prob = collect_problem_fields()

    new_pattern = {
        "id":       pat_id,
        "name":     name,
        **colors,
        "problems": [prob],
    }

    new_patterns = deepcopy(patterns)
    new_patterns.append(new_pattern)

    print(f"\n  ✓  Created new pattern «{name}» with problem «{prob['title']}».")
    return new_patterns

def add_to_existing_group(patterns: list) -> list:
    """Add a problem to an existing sub-pattern inside a group."""
    groups = [p for p in patterns if p.get("isGroup")]
    if not groups:
        print("  No pattern groups found.")
        return patterns

    print("\n  Groups:")
    numbered_list(groups, lambda g: g["name"])
    gchoice = pick("Select group", 1, len(groups))
    group   = groups[gchoice - 1]

    children = group["children"]
    print(f"\n  Sub-patterns of «{group['name']}»:")
    numbered_list(children, lambda c: f"{c['name']}  ({len(c['problems'])} problems)")
    cchoice = pick("Select sub-pattern", 1, len(children))
    child   = children[cchoice - 1]

    prob = collect_problem_fields()

    new_patterns = deepcopy(patterns)
    for p in new_patterns:
        if p["id"] == group["id"]:
            for c in p["children"]:
                if c["id"] == child["id"]:
                    c["problems"].append(prob)
                    break
            break

    print(f"\n  ✓  Added «{prob['title']}» to «{group['name']} → {child['name']}».")
    return new_patterns

def add_new_subpattern_to_group(patterns: list) -> list:
    """Add a new sub-pattern (with its own colours) to an existing group."""
    groups = [p for p in patterns if p.get("isGroup")]
    if not groups:
        print("  No pattern groups found.")
        return patterns

    print("\n  Groups:")
    numbered_list(groups, lambda g: g["name"])
    gchoice = pick("Select group", 1, len(groups))
    group   = groups[gchoice - 1]

    section(f"NEW SUB-PATTERN  (inside «{group['name']}»)")
    name   = ask("Sub-pattern name  (e.g. Kadane's Algorithm)")
    sub_id = slug(name)
    colors = pick_color(patterns)

    prob = collect_problem_fields()

    new_child = {
        "id":       sub_id,
        "name":     name,
        **colors,
        "problems": [prob],
    }

    new_patterns = deepcopy(patterns)
    for p in new_patterns:
        if p["id"] == group["id"]:
            p["children"].append(new_child)
            break

    print(f"\n  ✓  Added sub-pattern «{name}» with problem «{prob['title']}».")
    return new_patterns

def add_new_group(patterns: list) -> list:
    """Create a brand-new group pattern with one sub-pattern and one problem."""
    section("NEW GROUP PATTERN")
    gname  = ask("Group name  (e.g. Tree Patterns)")
    gid    = slug(gname)
    gcolors = pick_color(patterns)

    section(f"FIRST SUB-PATTERN  (inside «{gname}»)")
    cname  = ask("Sub-pattern name  (e.g. DFS)")
    cid    = slug(cname)
    ccolors = pick_color(patterns)

    prob = collect_problem_fields()

    new_group = {
        "id":       gid,
        "name":     gname,
        "isGroup":  True,
        **gcolors,
        "children": [
            {
                "id":       cid,
                "name":     cname,
                **ccolors,
                "problems": [prob],
            }
        ],
    }

    new_patterns = deepcopy(patterns)
    new_patterns.append(new_group)

    print(f"\n  ✓  Created group «{gname}» → sub-pattern «{cname}» with problem «{prob['title']}».")
    return new_patterns

def add_problem(patterns: list) -> list:
    section("ADD PROBLEM — WHERE?")
    options = [
        "Existing pattern  (regular, non-grouped)",
        "New pattern       (brand-new top-level pattern)",
        "Existing group    → existing sub-pattern",
        "Existing group    → new sub-pattern",
        "New group         (new grouped pattern + sub-pattern)",
    ]
    numbered_list(options)
    choice = pick("Select destination", 1, len(options))

    dispatch = [
        add_to_existing_pattern,
        add_new_pattern,
        add_to_existing_group,
        add_new_subpattern_to_group,
        add_new_group,
    ]
    return dispatch[choice - 1](patterns)

# ── DELETE ────────────────────────────────────────────────────────────────────

def delete_problem(patterns: list) -> list:
    section("DELETE PROBLEM")
    all_probs = flat_problems(patterns)
    if not all_probs:
        print("  No problems to delete.")
        return patterns

    numbered_list(all_probs, fmt_prob)
    choice = pick("Problem to delete", 1, len(all_probs))
    target = all_probs[choice - 1]

    if not confirm(f"Delete «{target['title']}»?"):
        print("  Cancelled.")
        return patterns

    new_patterns = deepcopy(patterns)
    path = target["_path"]
    idx  = target["_idx"]

    if len(path) == 1:                          # regular pattern
        for p in new_patterns:
            if p["id"] == path[0]:
                p["problems"].pop(idx)
                if not p["problems"]:
                    new_patterns.remove(p)
                    print(f"  🗑  Pattern «{p['name']}» is now empty — removed.")
                break

    else:                                       # group → child
        for p in new_patterns:
            if p["id"] == path[0]:
                for c in p["children"]:
                    if c["id"] == path[1]:
                        c["problems"].pop(idx)
                        if not c["problems"]:
                            p["children"].remove(c)
                            print(f"  🗑  Sub-pattern «{c['name']}» is now empty — removed.")
                        break
                # If the group itself has no children left, remove the group too
                if not p.get("children"):
                    new_patterns.remove(p)
                    print(f"  🗑  Group «{p['name']}» has no sub-patterns left — removed.")
                break

    print(f"\n  ✓  Deleted «{target['title']}».")
    return new_patterns

# ─── Main menu ────────────────────────────────────────────────────────────────

MENU_OPTIONS = [
    ("List all problems",   list_problems),
    ("Add a problem",       add_problem),
    ("Delete a problem",    delete_problem),
    ("Quit",                None),
]

def main():
    parser = argparse.ArgumentParser(
        description="Manage problems in DSA Pattern Sheet HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples
            --------
            python manage_patterns.py
            python manage_patterns.py --file ~/docs/Pattern_Sheet.html
        """),
    )
    parser.add_argument(
        "--file", "-f",
        default="Pattern_Sheet.html",
        help="Path to the HTML file  (default: Pattern_Sheet.html in current dir)",
    )
    args = parser.parse_args()

    filepath = os.path.expanduser(args.file)
    if not os.path.isfile(filepath):
        print(f"\n  ✗  File not found: {filepath}")
        sys.exit(1)

    print(f"\n  DSA Pattern Sheet Manager")
    print(f"  File → {os.path.abspath(filepath)}\n")

    html = load_html(filepath)
    try:
        js_block, start, end = extract_patterns_block(html)
        patterns = js_array_to_python(js_block)
    except Exception as e:
        print(f"\n  ✗  Failed to parse patterns from file:\n     {e}")
        sys.exit(1)

    while True:
        section("MAIN MENU")
        for i, (label, _) in enumerate(MENU_OPTIONS, 1):
            print(f"  [{i}] {label}")

        choice = pick("Choose action", 1, len(MENU_OPTIONS))
        label, fn = MENU_OPTIONS[choice - 1]

        if fn is None:          # Quit
            print("\n  Bye!\n")
            break

        if fn is list_problems:
            fn(patterns)
        else:
            new_patterns = fn(patterns)
            if new_patterns is not patterns:
                patterns = new_patterns
                try:
                    new_html = rebuild_html(html, patterns)
                    save_html(filepath, new_html)
                    html = new_html   # keep in sync for subsequent ops
                    print(f"  💾  Saved → {os.path.abspath(filepath)}")
                except Exception as e:
                    print(f"\n  ✗  Could not save file:\n     {e}")

        input("\n  Press Enter to return to menu…")


if __name__ == "__main__":
    main()
