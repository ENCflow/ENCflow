# Multilingual documentation and teaching-material policy

[日本語正本](../multilingual.md)

> English mirror of docs/multilingual.md. The Japanese file is the master copy.

Established 2026-10-23. This policy defines the layout, maintenance and review of
documents, teaching materials, sample settings and presentation assets. The
history of the language decisions is in [developer.md §34.2](../developer.md)
and the computational and verification rules are in [CLAUDE.md](../../CLAUDE.md)
(both in Japanese); this document is the operating policy built on them.

## 1. Authoritative versions

**Only `LICENSE` and `TRADEMARKS.md` are authoritative in English. All other
documents, teaching materials and sample settings are authoritative in
Japanese; English and future translations are mirrors.** The language shown
at an entry point does not determine authority.

| Material | Authoritative source | Translation or entry point |
|---|---|---|
| Root README | `README.ja.md` | `README.md` is the English mirror (GitHub landing page; §34.2) |
| License | `LICENSE` (English) | Any Japanese version must be identified as a reference translation |
| Name and trademarks | `TRADEMARKS.md` (English) | `TRADEMARKS.ja.md` is the Japanese mirror |
| Contribution guide | `CONTRIBUTING.md` (Japanese) | `CONTRIBUTING.en.md` |
| Other explanations, teaching materials and settings | Japanese version | Translation in the corresponding language directory |

Identify the source at the top of every translation (English files carry the
stamp "English mirror of <source path>"; §34.2). A mirror is not an abridgment
or a different lesson: retain the content, structure, equations, settings,
warnings and conclusions. Correct substantive content in the source first.
Translation-only corrections need not alter the source. Record scientific
questions or existing inconsistencies separately; do not silently correct them
while translating.

Do not create language-specific implementations of code, machine-readable
identifiers, data, existing rights notices or third-party originals. English
in those shared assets does not establish a new authoritative language
version. This policy does not change LICENSE, TRADEMARKS, NOTICE or
third-party rights notices. Program input and output (parameter names, the
Log, screen messages) are fixed in English and are not translated (§34.2).

## 2. Layout

Keep Japanese sources in their functional or case directories; place only
translations under `en/`. Do not move Japanese sources to `ja/` merely for
symmetry. Do not translate file or case names.

```text
docs/users_guide/time.md              → docs/en/users_guide/time.md
tutorials/README.md                   → tutorials/en/README.md
tutorials/wave/README.md              → tutorials/wave/en/README.md
tutorials/wave/param_step1.txt        → tutorials/wave/en/param_step1.txt
test/wave_river/README.md             → test/wave_river/en/README.md
examples/List_samples/list_wave.txt  → examples/List_samples/en/list_wave.txt
utils/<tool>/README.md                → utils/<tool>/en/README.md
```

For `docs/`, insert the language directory directly below its root. For
cases, insert it directly below the **independent execution unit**, retaining
relative paths below that point. An independent case at
`examples/benchmark/<case>/` therefore has its own `en/`. By contrast,
`test/wave/notes/detail.md` maps to `test/wave/en/notes/detail.md`.
The checker uses the nearest `Makefile` or `Run.sh` as an execution-unit
marker and also recognizes existing mirror locations. Review the mapping
when introducing a layout without such markers.

Retain the root README, CONTRIBUTING and TRADEMARKS exceptions above.
Keep `CLAUDE.md` as an existing entry point referring to this policy.
The suffix layout used so far for single-file English versions
(`test/README.en.md`, `examples/README.en.md`, `bmi/README.en.md`,
`utils/<tool>/README.en.md`) remains valid (the checker only reports it as a
WARN and does not require migration). Place new translations in the `en/`
layout and do not add new suffix-style files. Additional languages, such as
`fr/` and `zh-CN/`, follow the same rules. When introducing a new language
code, also register it in the checker's `LOCALES` so that an audit of another
language does not mistake its translations for Japanese sources.

## 3. Translated versus shared assets

| Type | Treatment |
|---|---|
| README files, explanations, procedures, figure captions | Translate |
| Sample namelist settings | Translate comments where useful |
| Numerical code, execution/input-generation/check scripts, Makefiles | Share; do not duplicate by language |
| DEM, rain, boundary inputs, reference data, save/restore files, results | Share; do not translate |
| Language-independent figures | Reference the same file |
| Figures and display settings containing language-specific labels | Allow separate presentation assets only where necessary |
| Notebooks | Translate explanatory cells; keep code cells shared except comments and display strings |

The scope is as follows. Sources that do not require a translation are
registered as patterns in `tools/i18n/scope.json` and reported as
`not-required` by the audit (this does not affect pairs whose translation
exists).

- All user-facing documents in `docs/` (users_guide, install, tutorial,
  comparison, ai_guide, windows and this policy) are in scope. Developer
  documents (developer.md, handoff, `*_plan.md`, `*_design.md`,
  channel_model.md, architecture.md, icon/) are out of scope (§34.2; to be
  reconsidered as internationalization progresses).
- `tutorials/` treats explanations and annotated inputs as a pair; all are in scope.
- The case descriptions (README) in `test/` are covered progressively, all of
  them. English comments for their parameter files are optional, starting
  with those that aid understanding.
- All of `examples/List_samples/` is in scope, because the comments
  themselves are the reference.
- The figures embedded in a `test/` README are drawn in an English-labelled
  version into `en/figs/` by the `en` argument of the plotting script (Fig.py
  etc.), and the English README refers to them (2026-10-24; the drawing code
  and the data are shared, only the labels and the output directory switch;
  without the argument the script behaves as before).
- The README of every `examples/<case>/` (phenomenon-specific example) is in
  scope as well (§34.2 amended on 2026-10-23). Parameter files, plotting
  scripts and figures are shared; English comments are optional. The
  `list_*.txt` files of benchmark are out of scope.

### Presentation assets

Do not delete existing English presentation assets, such as
`tutorials/chichibu/en/figs/` or `en/Fig_chichibu.plt`, on the mistaken basis
that they duplicate execution assets. Keep numerical values, geometry,
coordinates, units, ranges and data processing shared; restrict differences
to presentation such as labels. For new work, prefer shared rendering logic
with separate label definitions. Refactoring existing scripts for sharing
must be a separately verified change, not part of adding translations.

Do not rerun the model to replace reference data or underlying results for
a translation. Rendering differently labeled figures from the same saved
results is allowed. Rendering equivalence is not automatically guaranteed:
review the versions of the source, presentation files and necessary data.
Changes to shared dependencies absent from the review registry are not
tracked automatically.

### Notebooks

Translate Markdown cells. In code cells, only comments (`#`, and `!` in an
embedded namelist) and display strings (such as print messages) may be
translated; all other code, values, paths, and the cell types and order stay
identical (the same discipline as "everything except comments is identical"
for sample settings). Implement any necessary multilingual code support in
shared code and verify it as a separate change. Saved outputs alone do not
establish a successful execution. Before publication, check the working
directory and execution order. A lesson with source explanations or warnings
removed is not a mirror.

## 4. Working directories and input equivalence

**For every language, work in the case directory, not in `en/`.** Markdown
links are relative to the document; commands and input paths are relative
to the working directory.

```bash
cd tutorials/wave
make
./encflow param_step1.txt       # Input with Japanese comments
# Alternatively, in the same working directory:
./encflow en/param_step1.txt    # Input with English comments
```

These are alternative procedures, not a way to retain separate output sets.
They use the same output paths, so consecutive runs in one working copy can
overwrite results. Use separate working copies for comparisons; do not
change `dir_result` or similar values for translation.

Only natural-language comments may change. Preserve namelist names,
variables, numbers, string and logical values, paths, assignment order and
enabled/disabled settings. Preserve the values, identifiers and order of
commented-out examples. Do not rewrite `fn_*` references. With multi-file
inputs, an English-commented entry file may still read shared authoritative
settings. A facility that prepares an entirely English-commented working
copy must be designed separately, not hidden in the translation process.

`test/<case>/Run.sh` and `Run_MPI.sh` continue using their authoritative inputs.
Do not switch test conditions or references by language. Distinguish direct
execution of a translated input from the official verification/regression run.

## 5. Links and migration

Where a same-language page exists, link explicitly to that page. Linking
only to a case directory can send readers back to its Japanese README.
Identify untranslated destinations as "(in Japanese)" or similar and point to
the source. Source and language-selector links may cross languages. The
English-authoritative legal documents (LICENSE, TRADEMARKS.md) are referenced
directly from English mirrors.

When moving documents, update relative page and image links. Do not apply
blanket replacements to commands in code blocks or parameter values. Check
heading anchors separately in each language. On moving a legacy
`README.en.md` into `en/`, leave only a short forwarding notice rather than a
second copy of its body. Mark the notice with `<!-- i18n-redirect -->`. This
is a checker marker, not an automatic redirect.

## 6. Review records

Use the sequence: update source → update translation → review content →
record the reviewed versions. Leave pending translations explicitly
unreviewed or stale; do not update hashes alone to declare completion.

`tools/i18n/reviews.json` records SHA-256 hashes of both versions, reviewer,
method (`human` or `assistant`) and date. Hash UTF-8 text with CRLF normalized
to LF; hash binary images as bytes. Never record an AI review as a human one.

| Status | Meaning |
|---|---|
| `missing` | No translation |
| `not-required` | No translation, and the source is declared out of scope in `scope.json` (§3) |
| `unreviewed` | Translation exists, but no reviewed-version record |
| `reviewed` | Both files match their recorded versions |
| `stale` | Source changed after review |
| `translation-changed` | Only the translation changed after review |
| `missing-source` | Source missing, including an unregistered orphan mirror |
| `shared-copy` | A shared execution/input asset was duplicated in a language directory |

`reviewed` records version agreement; it does not mechanically prove
translation accuracy or computational validity. Do not bulk-approve existing
mirrors. Without a review record, existence alone establishes neither that a
translation is current nor that it is outdated; use `unreviewed`. To
prioritize `unreviewed` pairs, use `--git-dates` (warns where the source's
last commit is newer than the translation's).

## 7. Checks

Use Python 3.9 or later and only its standard library. This introduces no
new dependency into the numerical model. Run from the repository root.

```bash
python3 -m unittest discover -s tools/i18n -p 'test_*.py' -v

# Inventory: missing/unreviewed translations alone do not fail (--all also lists not-required)
python3 tools/i18n/check.py audit --links --git-dates

# Check recorded pairs for changes and local links (the condition CI runs)
python3 tools/i18n/check.py audit --recorded-only --strict-recorded --links

# Machine-readable inventory; do not commit the generated report
python3 tools/i18n/check.py audit --json > /tmp/encflow-i18n-status.json

# After reviewing content, record one pair. For AI review use --method assistant.
python3 tools/i18n/check.py record docs/install.md docs/en/install.md \
  --reviewer 'Reviewer name' --method human
```

Discovery covers Markdown, notebooks and `param*.txt` / `list_*.txt` under
`docs/`, `tutorials/`, `test/`, `examples/`, `bmi/` and `utils/`. Register
arbitrarily named settings explicitly. Existing translated images, `.plt`
files and certain plotting Python files are detected, but shared images
are not all required to have translations. Vendor, result, reference, save
and build directories are excluded. In a Git working copy, inspect tracked
and non-ignored untracked files, not ignored temporary files. Discovery does
not understand every possible file type.

`--language fr` checks French pairs without mixing in recorded English pairs.
An English audit also checks existing Japanese mirrors of the exceptional
English-authoritative legal documents. `--strict` also fails on missing and
unreviewed translations, so it is normally inappropriate during rollout.
Exit codes are 0 for satisfying the selected conditions, 1 for failed checks
and 2 for invalid input or read errors.

What is checked, and the limits:

- **Namelists**: string-aware lexical comparison, not semantic parsing. The
  active input (after removing comments) must match exactly (ERROR).
  Single-line commented-out assignment examples (right-hand side consisting of
  values only) are also compared (ERROR). Prose such as "`! dt = 0.05 を使う`"
  is not treated as an example. Multiline examples require manual review (WARN).
- **Notebooks**: cell types and order, and the code with comments and string
  literals removed, must match (ERROR). Differences in string literals are a
  WARN (a person confirms they are display text). Nothing is executed.
- **Markdown structure**: differences in the sequence of heading levels and in
  the number of table rows are reported as WARN (mirrors keep the structure).
  A missing stamp or link naming the source within the first 30 lines is a WARN.
- **`--links`**: checks local targets of ordinary Markdown inline links, images
  and reference definitions, plus some cross-language mistakes (GitHub
  footnote definitions `[^key]:` are excluded). It is not a complete Markdown
  parser. HTML, heading anchors, external URL availability and links inside
  notebooks are not checked.
- People must review semantic equivalence of rendering scripts/images and the
  equations, values and code examples embedded in prose. Do not describe a
  passing static check as successful model execution, MPI identity or
  reference agreement.

## 8. Operation

- When a source changes, update the translation in the same piece of work,
  review the content and then `record` it. If it cannot be updated, leave it
  `stale` and note the pending update in `docs/handoff.md`.
- CI (`.github/workflows/i18n.yml`) requires only the unit tests and the
  "recorded pairs: no pending updates, links valid" check (introduced after
  inspecting the initial full-repository audit of 2026-10-23). Existing
  untranslated or unreviewed documents are not failure conditions. Moving to
  `--strict` is decided once the unreviewed pairs have been worked through.
  The same CI runs `tools/params_index/check.py`, which checks the full
  parameter index (ja/en) against the namelist declarations in `src/*.f90`
  (missing or extra rows, ordering, ja/en correspondence, the stated entry
  count, and the mention of each name in its chapter page; developer.md
  §35.1; introduced 2026-10-24).
- Do not move or delete existing Japanese sources. Keep rendering
  refactoring and execution-mechanism changes separate from translations.
  Translation work must not change numerical code, authoritative numerical
  inputs or regression references.
- Existing inconsistencies found by the initial audit (such as outdated
  English List_samples files) are listed in `docs/handoff.md` and resolved
  progressively as translation updates.
