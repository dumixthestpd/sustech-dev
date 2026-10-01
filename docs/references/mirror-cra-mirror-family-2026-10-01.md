---
title: The CRA open-source mirror — paths, listings, training programs
service: mirror
captured: 2026-10-01
---

# The CRA open-source mirror (mirrors.sustech.edu.cn)

Public, unauthenticated. Maintained by SUSTech CRA; content is
**CC-BY-SA-4.0** (keep the attribution when you pass a file on). It is the
fastest source for course syllabi and undergraduate training plans, and it
needs no CAS session — the exception is `mirror course`, which reads TIS
catalog/grade data and therefore wants a TIS session.

Everything below was re-checked live on 2026-10-01 in both lanes
(`sustech-cli` TypeScript, `sustech_survival` Python).

## Paths

| Content | Path |
|---|---|
| One syllabus PDF | `/courses/syllabus/<CODE>.pdf` |
| Syllabus HTML rendering | `/courses/syllabus/html/<CODE>.html` |
| Syllabus directory listing | `/courses/syllabus/` |
| Undergraduate training programs | `/courses/本科人才培养方案/` |
| Campus map | `/site/sustech-online/documents/campus-map/…` |

## 🔴 A raw UTF-8 path is a 404

The mirror is fronted by nginx and **answers 404 to a raw UTF-8 path**.
`requests` and `fetch()` percent-encode silently, so a client that prints the
URL it built looks correct while every link it hands a human or a script is
dead:

```text
raw:      /courses/本科人才培养方案/2024级本科人才培养方案.pdf   → 404 (curl, wget, scripts)
encoded:  /courses/%E6%9C%AC%E7%A7%91%E4%BA%BA%E6%89%8D%E5%9F%B9%E5%85%BB%E6%96%B9%E6%A1%88/…  → 200
```

Build URLs already encoded, in one place, and use that same string for
probing, printing and fetching. Python: `urllib.parse.quote` per segment
(`_program_base()` / `_program_stem()`). TypeScript: `encodeURIComponent`
(`PROGRAM_PREFIX_ENCODED`). Browsers encode on their own, which is exactly why
this bug survives manual testing.

## Directory listings are nginx autoindex HTML

`<a href="…">name</a>` rows, percent-encoded hrefs, directories ending in `/`;
skip `../`, `/`, empty and `?`-prefixed hrefs. One parser per codebase:
Python `mirror/cli.py::_autoindex_rows` (+ `_pdf_rows` for the PDFs), TypeScript
`MirrorClient.parseIndexEntries` over `fetchIndexHtml`. Show the **decoded**
name to humans and use the **encoded** href for links.

## Training programs: 2019–2024 are directories, not files

Only the newest year is a single whole-school PDF. Every earlier year is a
*directory* of per-major PDFs — 2024级 holds **42** of them:

```text
00-2024级通识培养方案.pdf
01-2024级金融数学专业本科人才培养方案.pdf
02-2024级数学与应用数学专业本科人才培养方案.pdf
…
2024级各专业理工类通识必修课程修读要求情况一览表.pdf
```

Consequences, all of which were bugs before 2026-10-01:

- **Never guess `<year>本科人才培养方案.pdf`.** Probe the file, then the
  directory (`resolveTrainingProgram` / `_program_kind`) and print only a URL
  that answers 200.
- **`--all` takes the directory, `--index NN` one major** (both lanes).
- A bare `get <year>` takes the `00-…通识培养方案.pdf` that anchors the
  directory — the same file both lanes fetch by default (verified identical:
  635,600 bytes for 2024级).
- `program years` HEAD-probes candidates, remembering the trailing slash for
  directory years.

## Command surface (keep the two lanes in step)

| | TypeScript (`sustech-cli`) | Python (`sustech_survival`) |
|---|---|---|
| syllabi | `mirror syllabus url\|exists\|get\|text` | + `extract` alias, `open`, `list-departments`, `batch` |
| programs | `mirror program years\|url\|list\|get [--all\|--index NN]` | same |
| other | `mirror map get`, `mirror handbook get`, `mirror list`, `mirror course` | + `mirror course --text/--include-raw` |

Discoveries travel both ways; the fork rule is that features start on the
Python side and the TS lane is brought to parity (here: `program url` came
from TS, `program list` and the encoding law from Python).

## Verified 2026-10-01

- `program url 2024级 2025级` → directory URL and PDF URL, **both 200 to curl**
  (previously 404).
- `program list 2024级` → 42 rows of `name<TAB>encoded url`; the first answers 200.
- `program get 2024级` → `00-2024级通识培养方案.pdf`, 635,600 bytes, identical in
  both lanes; `--index 40` → 1,690,369-byte per-major PDF starting `%PDF-`.
- `mirror syllabus url CLE022` → `https://mirrors.sustech.edu.cn/courses/syllabus/CLE022.pdf`.
