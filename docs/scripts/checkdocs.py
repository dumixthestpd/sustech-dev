#!/usr/bin/env python3
"""Content lint for the sustech-dev docs — the rot `mkdocs build --strict` cannot see.

Checks, all with the standard library only (so CI needs no install):

1. every `docs/references/*.md` is listed in `mkdocs.yml` (an unlisted note is
   invisible to readers, which is how a catalog quietly loses entries),
2. every `references/...md` nav entry exists,
3. every relative markdown link in `docs/**/*.md` resolves,
4. `docs/SKILL.md` frontmatter keeps `name` and a substantial `description`,
5. any `captured:` frontmatter value is `YYYY-MM-DD`.

Exit code 0 = clean, 1 = something to fix (each finding printed).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"

LINK_RE = re.compile(r"\]\(([^)]+)\)")
FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
# Only docs-internal links are checked: a path to another repo (a logo, a module
# file) is prose, and a README-shaped snippet is not a link target at all.
CHECKABLE = re.compile(r"[A-Za-z0-9._%/\-]+\.(?:md|yml|yaml)")
FENCED = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def frontmatter(path: pathlib.Path) -> dict[str, str]:
    match = FRONT_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def check_nav_coverage(nav_text: str, problems: list[str]) -> None:
    for note in sorted((DOCS / "references").glob("*.md")):
        if note.name not in nav_text:
            problems.append(f"reference not listed in mkdocs.yml: references/{note.name}")


def check_nav_targets(nav_text: str, problems: list[str]) -> None:
    for entry in set(re.findall(r"references/[\w\-.%]+\.md", nav_text)):
        if not (DOCS / entry).exists():
            problems.append(f"mkdocs.yml nav points at a missing file: {entry}")


def check_links(problems: list[str]) -> None:
    checked = 0
    for page in sorted(DOCS.rglob("*.md")):
        text = FENCED.sub("", page.read_text(encoding="utf-8"))
        text = INLINE_CODE.sub("", text)
        for raw in LINK_RE.findall(text):
            target = raw.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0].split(" ", 1)[0]
            if not CHECKABLE.fullmatch(target):
                continue
            checked += 1
            if not (page.parent / target).exists():
                problems.append(f"broken link in {page.relative_to(ROOT)}: {raw.strip()}")
    print(f"checked {checked} relative doc links")


def check_skill_frontmatter(problems: list[str]) -> None:
    fields = frontmatter(DOCS / "SKILL.md")
    if not fields.get("name"):
        problems.append("docs/SKILL.md frontmatter is missing `name`")
    description = fields.get("description", "")
    if len(description) < 40:
        problems.append("docs/SKILL.md frontmatter `description` is missing or too short to trigger")


def check_dates(problems: list[str]) -> None:
    for note in sorted((DOCS / "references").glob("*.md")):
        captured = frontmatter(note).get("captured")
        if captured and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", captured):
            problems.append(f"{note.relative_to(ROOT)}: captured: {captured} is not YYYY-MM-DD")


def main() -> int:
    if not MKDOCS.exists():
        print("mkdocs.yml not found — run from the repo root", file=sys.stderr)
        return 1
    nav_text = MKDOCS.read_text(encoding="utf-8")
    problems: list[str] = []
    check_nav_coverage(nav_text, problems)
    check_nav_targets(nav_text, problems)
    check_links(problems)
    check_skill_frontmatter(problems)
    check_dates(problems)

    if problems:
        print(f"{len(problems)} problem(s):")
        for item in problems:
            print(f"  - {item}")
        return 1
    count = len(list((DOCS / "references").glob("*.md")))
    print(f"checkdocs: OK — {count} references, all listed; links, frontmatter and dates clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
