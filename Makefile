# MAYA - Migration Accelerator
# Common developer tasks. `make demo` runs the full six-stage flow on the Northwind
# example with the deterministic offline agent driver (zero external calls).
CONFIG ?= examples/northwind/northwind.yaml
PY ?= python3

.PHONY: help demo \
	stage1 stage2 stage3 stage4 stage5 stage6 \
	graph order verify context orchestrate sample validate certify report bi \
	score replicate specs build docs publish run test figures clean

help:
	@echo "MAYA targets:"
	@echo "  make demo      - run the full six-stage flow on Northwind (offline driver)"
	@echo "  make stage1..6 - run an individual stage"
	@echo "  make test      - run the pytest suite"
	@echo "  make figures   - regenerate blog figures (needs Pillow)"
	@echo "  make report    - build the branded PDF report only"
	@echo "  make clean     - remove generated demo outputs"
	@echo ""
	@echo "  Six stages: 1 collect+score  2 replicate  3 specs"
	@echo "              4 conformance+build+certify  5 BI  6 docs+publish"
	@echo "  Primitives (still usable directly): graph order verify context"
	@echo "              orchestrate sample validate certify report bi"

# ---- full flow -----------------------------------------------------------
demo:
	$(PY) cli.py run --stage all --config $(CONFIG)
	@echo ""
	@echo "MAYA six-stage demo complete. Artifacts in examples/northwind/out/"

# ---- the six stages ------------------------------------------------------
stage1:
	$(PY) cli.py run --stage 1 --config $(CONFIG)

stage2:
	$(PY) cli.py run --stage 2 --config $(CONFIG)

stage3:
	$(PY) cli.py run --stage 3 --config $(CONFIG)

stage4:
	$(PY) cli.py run --stage 4 --config $(CONFIG)

stage5:
	$(PY) cli.py run --stage 5 --config $(CONFIG)

stage6:
	$(PY) cli.py run --stage 6 --config $(CONFIG)

# ---- stage-command aliases ----------------------------------------------
score:
	$(PY) cli.py score --config $(CONFIG)

replicate:
	$(PY) cli.py replicate --config $(CONFIG)

specs:
	$(PY) cli.py specs --config $(CONFIG)

build:
	$(PY) cli.py build --config $(CONFIG)

docs:
	$(PY) cli.py docs --config $(CONFIG)

publish:
	$(PY) cli.py publish --config $(CONFIG)

run:
	$(PY) cli.py run --stage $(STAGE) --config $(CONFIG)

# ---- primitives (unchanged; the stages call these under the hood) --------
graph:
	$(PY) cli.py graph --config $(CONFIG)

order:
	$(PY) cli.py order --config $(CONFIG)

verify:
	$(PY) cli.py verify --config $(CONFIG)

context:
	$(PY) cli.py context --config $(CONFIG)

orchestrate:
	$(PY) cli.py orchestrate --status --config $(CONFIG)

sample:
	$(PY) cli.py maya sample --config $(CONFIG) --pipeline nw_build_sales

validate:
	$(PY) cli.py validate --config $(CONFIG) --pipeline nw_build_marts --env soak

certify:
	$(PY) cli.py certify --config $(CONFIG) --gates examples/northwind/out/gates.json

report:
	$(PY) cli.py report --config $(CONFIG)

bi:
	$(PY) cli.py bi run --config $(CONFIG)

test:
	$(PY) -m pytest

figures:
	$(PY) blog/figures/generate_figures.py

clean:
	rm -rf examples/northwind/out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
