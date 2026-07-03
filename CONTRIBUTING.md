# Contributing to MAYA

Thanks for your interest in improving MAYA. This project turns a data-platform
migration into a deterministic, reviewable engineering process, and contributions
that keep it deterministic, source-agnostic, and well-tested are very welcome.

## Ground rules
- Be kind. See the [Code of Conduct](CODE_OF_CONDUCT.md).
- By contributing, you agree your work is licensed under the [Apache-2.0](LICENSE)
  license (see "Submission of Contributions" in the license text).
- Keep the core **source-agnostic**. Anything source-specific belongs in an adapter
  under `adapters/`, not in `core/`.
- Keep everything **deterministic**: same inputs -> same outputs. Sampling uses a fixed
  seed; ordering is a pure function of the graph. Tests assert on exact goldens.

## Getting set up
```bash
git clone https://github.com/vasutechgenie/maya-migrate-to-databricks
cd maya-migrate-to-databricks
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
make demo    # runs the full pipeline on the Northwind example
make test    # runs the test suite
```

## Making a change
1. Open an issue describing the problem or proposal first for anything non-trivial.
2. Create a branch, make focused commits.
3. Add/adjust tests. If you change classification, ordering, sampling, or the
   validation gate, update the Northwind goldens in `tests/` accordingly and explain
   why in the PR.
4. Run `make test` and `make demo` locally; both must be green.
5. Do **not** add any real customer/company names, credentials, internal hostnames,
   or absolute local paths. CI fails the build if it finds them.
6. Open a PR using the template; describe the change and its effect on the demo.

## What makes a good adapter contribution
An adapter emits the normalized graph (`objects.csv` / `edges.csv`), a DDL index, and a
connection inventory. See [docs/12_adapter_authoring_guide.md](docs/12_adapter_authoring_guide.md)
and the reference `adapters/synapse/`. New adapters should ship with a small synthetic
example (like `examples/northwind/`) so they are runnable and testable offline.

## Style
- Python, standard library first; new runtime dependencies need a good reason.
- Prefer small, pure functions. SQL generation stays in `core/validation.py` /
  `core/maya.py`. Docstrings explain intent, not mechanics.
