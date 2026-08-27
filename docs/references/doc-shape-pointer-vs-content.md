# Doc shape — pointer + content documents (added 2026-08-03)


User feedback (verbatim, paraphrased): *"all the docs should be in the structure of a big outline with pointers, and then maybe a subpointer to something, and then there's the final explanation on the details in one section or one module. We need to fix that and make it more reasonable, not just to stack everything together."*

Concrete pattern for module documentation:

```
docs/en/<module>.md                 pointer doc — outline tree, no content
├─ 1. Where things live             (files, sections, vars — pure index)
├─ 2. The <contract-name>           (→ see top docstring of source file)
├─ 3. <other facts>                 (→ see <other source files>)
└─ 4. Why this shape                (meta — only if useful)

src/<module>/<file>.py              the actual contract lives here
   file-level docstring             restates the contract so the file is
                                    self-contained for a reader who lands
                                    on it cold (still facts only, no
                                    workflow)
```

Three rules:

1. **Pointer doc = outline only.** Tree (root → branches → leaves), not a flat table of contents and not a content document. Each branch is a one-line pointer to where the content lives. Don't repeat the content in the pointer.
2. **Content lives next to the code it describes.** Cascade contracts in the file that owns the mutators. Route tables in the blueprint that serves them. CSS in the template. Top-of-file docstrings repeat module-doc facts so a reader doesn't have to context-switch — but the docstring is still facts only.
3. **One fact, one place.** If a fact is in two locations, one of them is stale. Pick the canonical home (next to the code) and the other is a pointer.
