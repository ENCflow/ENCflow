# Contributing to ENCflow

> English mirror of CONTRIBUTING.md. The Japanese file is the master copy.

Thank you for your interest in ENCflow. The current ways to help are
as follows.

## Questions and consultations (welcome)

Usage questions, "not sure if it's a bug", and consultations about
what you want to compute are all welcome in
[Discussions](https://github.com/ENCflow/ENCflow/discussions). No
question is too basic. If it turns out to be a bug, we will convert
it into an Issue.

## Bug reports and feature requests (welcome)

For clear-cut cases, please use
[Issues](https://github.com/ENCflow/ENCflow/issues) (when in doubt,
Discussions is fine).
Following the templates and including the items below speeds things
up considerably:

- **Bug reports**: steps to reproduce (the commands you ran), the
  parameter file (and any small data needed to reproduce), the tail of
  `result/Log.txt` and of the screen output, and your environment
  (OS, compiler + version, serial/MPI).
- **Feature requests**: tell us **what you want to compute** (the
  phenomenon) rather than how to implement it. If the
  [use-case gallery](docs/en/users_guide/usecases.md) has a similar
  phenomenon, mention it. If your case can be handled by combining
  existing features we will answer with the settings; if a new
  mechanism is needed we will file it as a plan.

## About code pull requests (not accepted for now)

Changes to ENCflow are quality-assured by taking each one through
bit-identical verification against the regression baselines. Until
this verification-backed review process can be run reliably for
external contributions, code pull requests are not accepted. Please
raise code-related findings and proposals in Issues instead — the
development team will implement them (with credit to the proposer).
Documentation corrections are also welcome via Issues.

Note that under [Apache-2.0](LICENSE) you are **entirely free to fork
and modify** ENCflow. Results and insights from forks are welcome in
Issues and Discussions.

## For those interested in the internals

Start with [docs/architecture.md](docs/architecture.md) (the one-page
map; currently in Japanese), and see
[docs/developer.md](docs/developer.md) for design decisions and
conventions. The verification discipline for changes (regression
baselines, bit reproducibility) is summarized in
[CLAUDE.md](CLAUDE.md). Local verification runs through each
`test/<case>/Run.sh` (automatic comparison against the baselines).
