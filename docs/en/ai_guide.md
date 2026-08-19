# Using ENCflow with AI agents (a guide for users)

> English mirror of docs/ai_guide.md. The Japanese file is the master copy.

Because all of ENCflow's input and output is text, you can have an AI
coding agent (an AI that operates from the terminal or editor, editing
files and running commands) **build cases from a description of the
phenomenon in plain words**. In fact, much of the development and
verification of ENCflow itself is carried out in collaboration with AI
agents. This page is for people who want to delegate case building,
execution, and analysis to an AI **as a user** — not as a developer.

## Getting started

With a CLI-type agent (e.g. Claude Code; the idea is the same for
other CLI or IDE-integrated agents), just start it in the cloned
repository directory and the agent recognizes the whole repository —
code, documentation, and examples:

```bash
cd ENCflow
claude        # or the launch command of your agent
```

With Claude Code, the slash command **`/make-case`** bundled in this
repository becomes available automatically. It encodes the standard
case-building procedure described below — try it first:

```
/make-case a snowmelt-flood-like phenomenon involving snowmelt and frozen ground
```

> **Note**: `/make-case` is merely an entry point that packages the
> standard procedure. You can also **talk to the agent in plain
> language** — the example instructions below are all plain requests
> without any slash command. Modifying an existing case is just as
> direct: "change the roughness rn0 in work/mycase/param.txt to 0.03,
> rerun, and compare the depth distribution with the previous result".
> The conversation continues, so you can iterate on what you see:
> "stronger rain", "put the figures side by side". Compound tasks —
> batch sensitivity runs over many cases, a simple calibration against
> observations, writing up a report of the results — can all be
> delegated as long as you can describe the procedure in words.

The agent asks for permission before creating files or running
commands (or approves automatically, depending on your settings and
plan). Until you are comfortable, reviewing and approving each action
is the safe way to work.

## What kinds of instructions work

You do not need to figure out the feature combination yourself — ask
in the words of the phenomenon. The agent looks the phenomenon up in
the [use-case gallery](users_guide/usecases.md), checks the parameters
in the [User's Guide](users_guide.md) chapters and
[List_samples](../examples/List_samples/), and assembles the case
(parameter file plus terrain or other data as needed).

Three tips for writing instructions:

1. **State the success criterion** — one sentence on "what should be
   visible if it worked". The agent runs the case and checks the Log
   and outputs against it by itself.
2. **Specify the working location** — have it build under `work/` or
   similar, outside the bundled examples (test/, examples/). If you
   forget, the agent may keep asking where to save things, or pick a
   location on its own judgment (`/make-case` is defined to build
   under work/, so there you can omit it).
3. **Ask for verification and figures** — writing "run it, check the
   water budget in the S column of the Log, and plot the result"
   prevents fire-and-forget case generation.

### Example instructions

> Build a minimal case in work/ where a 100 mm/h rainstorm falls for
> 30 minutes on a bowl-shaped terrain and the depression ponds up.
> You may generate the terrain with Python. Run it, confirm the S
> column is consistent with the rainfall volume, and plot the
> evolution of the water depth.

> Build a spring snowmelt-flood case in work/ involving snowmelt and
> infiltration suppression by frozen ground. See
> docs/users_guide/usecases.md for the features to use. Compare two
> cases, with and without frozen ground, and show in a figure that
> surface runoff increases with frozen ground.

> Starting from tutorials/chichibu/param_step5.txt, set up a
> sensitivity experiment in work/ with 1.5x the rainfall, and compare
> the hydrographs against the original case in one figure.

> For the seawater-intrusion case in test/salt, try raising the tide
> level by 0.2 m in work/ and report, in numbers, how the reach of
> the salt wedge changes.

## Rules the agent must follow (important)

These are also in the repository's CLAUDE.md (which agents read
automatically), but for user work in particular:

- **Never modify test/*/reference and never run `Run.sh -u`**
  (these are the regression baselines; breaking them destroys the
  verification machinery).
- Do not overwrite the bundled examples and tests — **work in a fresh
  location such as work/** (work/ is already in .gitignore).
- Building cases requires no changes to src/ (if the agent starts
  editing code unasked, stop it).

### Recovering from a broken state

If the agent's changes leave the repository in a strange state, it is
**faster and safer to start over** than to hunt for the cause: copy
your own products (the contents of work/, etc.) somewhere else, delete
the repository folder entirely, and clone it again. Think of a cloned
repository as a disposable box you can recreate any number of times —
as long as your own cases are backed up, nothing is lost.

## When it goes wrong

- If the agent seems unsure which features to use, tell it to read the
  [use-case gallery](users_guide/usecases.md).
- Parameter meanings are in the
  [full parameter index](users_guide/params_index.md) and the chapters;
  annotated examples are in
  [examples/List_samples](../examples/List_samples/) — a single "refer
  to ..." raises the accuracy noticeably.
- You can also delegate environment setup itself: "run make install in
  src and confirm that Run.sh in test/wave reaches PASS".
