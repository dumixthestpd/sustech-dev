# sustech-dev

SUSTech endpoint catalog + behavior notes for agents wrapping
[`sustech.edu.cn`](https://www.sustech.edu.cn) services.

A lean index (`SKILL.md`) + a `references/` folder of detailed notes.
Built to be loaded by agents that are wrapping `sustech.edu.cn`
endpoints, debugging a `操作失败`, or auditing a HAR against derived
code.

The companion Python module — `sustech_survival` — implements against
this catalog. If you find an endpoint behavior here that the module
gets wrong, open an issue or open a PR.

## When to load

- Wrapping a new `sustech.edu.cn` endpoint (auth shape, headers, cookies)
- Debugging a write-flow `操作失败` (HAR vs derived bytes, missing keys)
- Auditing cross-cutting gotchas (cookie rotation, XHR header, term/xn confusion)
- Reviewing design principles (module/UI split, API naming, docs philosophy)

## Install

```bash
npx skills add dumixthestpd/sustech-dev --skill sustech-dev
```

The skill lands at `~/.claude/skills/sustech-dev/`. Read it via:

```bash
npx skills add dumixthestpd/sustech-dev --skill sustech-dev --read
```

…or browse this site: <https://dumixthestpd.github.io/sustech-dev/>.

## Contributing

This is a catalog — every entry is a fact about a real endpoint. If
you find something wrong:

1. **Tip / advice / correction** — open an
   [issue](https://github.com/dumixthestpd/sustech-dev/issues) or start a
   [discussion](https://github.com/dumixthestpd/sustech-dev/discussions).
   No PR required for a question.
2. **Fix a wrong fact** — open a PR with the corrected `references/*.md`
   entry. Cite the HAR / capture date if applicable.
3. **Add a new endpoint note** — open a PR with a new file under
   `references/`, named `<service>-<topic>-<YYYY-MM-DD>.md`, then add
   a one-line link in `SKILL.md` under the right section.

## Repo layout

```
sustech-dev/
├── README.md          this file (humans browsing the repo)
├── SKILL.md           the skill definition (loaded by agents)
├── mkdocs.yml         mkdocs config — generates the docs site
├── references/        detailed endpoint / behavior notes
└── scripts/           reusable probes (run before designing new integrations)
```

## Source of truth

The repo **is** the source of truth. The docs site is a render of it.

## See also

- `sustech_survival` (Python module): <https://github.com/dumixthestpd/sustech_survival>
- `sustech-skill` (agent knowledge): <https://github.com/dumixthestpd/sustech-skill>
- SUSTech: <https://www.sustech.edu.cn>