#!/usr/bin/env python3
"""
Wrap Japanese text into caption lines at natural phrase (bunsetsu) boundaries.

Every burned-in-caption script in this toolkit used to hand-roll line wrapping
by searching backwards from a character budget for the nearest 。！？…、 —
which breaks mid-phrase whenever no punctuation falls in range (e.g.
"視界の中に自分にしか" has to be cut somewhere with zero commas nearby).
BudouX (Google's open-source Japanese line-break segmenter, see
https://github.com/google/budoux) parses text into phrase chunks and never
splits inside one, so wrapping always lands on a readable boundary.

Added via skill-discovery audit, 2026-09-10 — see pyproject.toml's `editing`
extra (`uv sync --extra editing`).

Usage as a library:
    from tools.jp_wrap import wrap_jp
    lines = wrap_jp("ENTPが童貞のまま拗らせると、視界の中に自分だけが正しいと思ってる人格が現れる。", budget=14)

Usage as a CLI (quick check / piping from another script):
    uv run tools/jp_wrap.py "ここに長い日本語のテキストを入れる" --budget 14
    echo "テキスト" | uv run tools/jp_wrap.py --budget 16
"""
import argparse
import sys

_parser = None


def _get_parser():
    global _parser
    if _parser is None:
        import budoux
        _parser = budoux.load_default_japanese_parser()
    return _parser


def wrap_jp(text: str, budget: int = 14) -> list[str]:
    """Wrap `text` into lines of at most ~`budget` characters, breaking only
    between BudouX phrase chunks (never inside one). A single chunk longer
    than `budget` is kept whole on its own line rather than split mid-phrase —
    for burned captions that's the right trade-off (a slightly long line beats
    a broken phrase)."""
    if not text:
        return []
    chunks = _get_parser().parse(text)
    lines: list[str] = []
    cur = ""
    for chunk in chunks:
        candidate = cur + chunk
        if cur and len(candidate) > budget:
            lines.append(cur)
            cur = chunk
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="Text to wrap (reads stdin if omitted)")
    ap.add_argument("--budget", type=int, default=14, help="Target max characters per line (default: 14)")
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read().strip()
    for line in wrap_jp(text, args.budget):
        print(line)


if __name__ == "__main__":
    main()
