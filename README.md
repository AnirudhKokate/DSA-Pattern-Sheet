# DSA Pattern Sheet

A clean, self-contained HTML cheat sheet for tracking DSA (Data Structures & Algorithms) problems organised by pattern — with a companion Python script for managing problems without touching any HTML by hand.

---

## What it is

**DSA Pattern Sheet** is a single-file study tracker that groups LeetCode, GeeksForGeeks, and Coding Ninjas problems by the algorithmic pattern they exercise. Instead of a flat list of problems, you see them grouped under patterns like *Two Pointers*, *Sliding Window*, *Prefix Sum*, or *Moore's Voting* — so you study the *idea*, not just the problem.

Everything lives in one HTML file you can open directly in a browser. No server, no build step, no dependencies.

---

## Features

| Feature | Details |
|---|---|
| **Pattern grouping** | Problems organised under named patterns; related patterns can be nested under a group with a tab interface |
| **Shuffle** | Picks a random problem across all patterns and shows it in a toast popup with a direct solve link |
| **Jump to problem** | From the shuffle toast, jump straight to the problem's row in the sheet |
| **Search** | Live-filters problems and patterns as you type |
| **Sidebar navigation** | Sticky sidebar with pattern links; active section highlighted as you scroll |
| **Section glow** | Navigating to a section triggers a subtle glow animation to orient you |
| **Responsive** | Collapses sidebar to a hamburger menu on mobile |
| **Dark theme** | Carefully tuned dark UI with per-pattern accent colours |

---

## File structure

```
.
├── Pattern_Sheet.html     # The entire app — open this in a browser
└── manage_patterns.py     # CLI tool to add / remove problems
```

---

## Opening the sheet

Just open `Pattern_Sheet.html` in any modern browser. No internet connection required after the Google Fonts load on first open (fonts are cached thereafter).

```bash
# macOS
open Pattern_Sheet.html

# Linux
xdg-open Pattern_Sheet.html

# Windows
start Pattern_Sheet.html
```

---

## Managing problems — `manage_patterns.py`

The Python script lets you add or delete problems through an interactive menu without editing any HTML directly.

### Requirements

- Python 3.8+
- Node.js (optional but recommended — used for robust JS parsing; falls back to a pure-Python parser if absent)

### Usage

```bash
# Run from the same directory as Pattern_Sheet.html
python manage_patterns.py

# Or point it at a file elsewhere
python manage_patterns.py --file ~/docs/Pattern_Sheet.html
```

### Menu options

```
[1] List all problems
[2] Add a problem
[3] Delete a problem
[4] Quit
```

### Adding a problem

Choosing **Add** presents five destinations:

| Option | When to use |
|---|---|
| Existing pattern | Add to a pattern that already exists (e.g. Two Pointers) |
| New pattern | Create a brand-new top-level pattern with an auto-assigned colour |
| Existing group → existing sub-pattern | Add to a sub-pattern inside a group (e.g. Array Patterns → Prefix Sum) |
| Existing group → new sub-pattern | Add a new tab inside an existing group |
| New group | Create a brand-new grouped pattern with its first sub-pattern |

You'll be prompted for:

- **Problem title** — e.g. `3Sum`
- **LeetCode number** — e.g. `15` (optional; press Enter to skip for GFG/CN problems)
- **Platform** — `lc` (LeetCode) · `gfg` (GeeksForGeeks) · `cn` (Coding Ninjas / Naukri)
- **URL** — direct link to the problem

Colours for new patterns are picked automatically from a curated palette that avoids duplicating colours already in use.

### Deleting a problem

Choose **Delete**, pick a problem from the numbered list, and confirm. If deleting a problem leaves a pattern (or sub-pattern, or group) empty, that container is automatically removed too.

---

## Data format

Problems are stored as a JavaScript array literal inside the HTML file. Each entry looks like this:

```js
// Regular pattern
{
  "id": "two-pointers",
  "name": "Two Pointers",
  "color": "#6c5fc7",
  "bg": "#f0effe",
  "border": "#d8d4f8",
  "problems": [
    {
      "title": "Move Zeroes",
      "lc": 283,
      "platform": "lc",
      "url": "https://leetcode.com/problems/move-zeroes/"
    }
  ]
}

// Grouped pattern (rendered as a tabbed panel)
{
  "id": "array-patterns",
  "name": "Array Patterns",
  "isGroup": true,
  "color": "...", "bg": "...", "border": "...",
  "children": [
    {
      "id": "prefix-sum",
      "name": "Prefix Sum",
      "color": "...", "bg": "...", "border": "...",
      "problems": [ ... ]
    }
  ]
}
```

You can also edit this block directly in any text editor if you prefer.

---

## Supported platforms

| Code | Platform |
|---|---|
| `lc` | LeetCode |
| `gfg` | GeeksForGeeks |
| `cn` | Coding Ninjas / Naukri Code360 |

---

## Customisation

All visual tokens are CSS custom properties at the top of the `<style>` block in `Pattern_Sheet.html`. You can change the background, surface, border, and text colours there without touching any JavaScript.

Per-pattern colours (`color`, `bg`, `border`) live in the `patterns` array in the `<script>` block and are applied via inline CSS variables at render time.

---

## License

This project is for personal study use. Do whatever you like with it.
