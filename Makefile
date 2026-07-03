# MAYA - Migration Accelerator
# Common developer tasks. `make demo` runs the full pipeline on the Northwind example.
CONFIG ?= examples/northwind/northwind.yaml
PY ?= python3

.PHONY: help demo graph order verify context orchestrate sample validate certify report bi test figures clean

help:
	@echo "MAYA targets:"
	@echo "  make demo      - run graph->order->verify->context->orchestrate->sample->validate->certify->report->bi on Northwind"
	@echo "  make test      - run the pytest suite"
	@echo "  make figures   - regenerate blog figures (needs Pillow)"
	@echo "  make report    - build the branded PDF report only"
	@echo "  make certify   - whole-system rollup (is the migration complete?)"
	@echo "  make clean     - remove generated demo outputs"

demo: graph order verify context orchestrate sample validate certify report bi
	@echo ""
	@echo "MAYA demo complete. Artifacts in examples/northwind/out/"

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
	$(PY) cli.py certify --config $(CONFIG)

report:
	$(PY) cli.py report --config $(CONFIG)

bi:
	$(PY) cli.py bi extract --config $(CONFIG)
	$(PY) cli.py bi genie --config $(CONFIG)

test:
	$(PY) -m pytest

figures:
	$(PY) blog/figures/generate_figures.py

clean:
	rm -rf examples/northwind/out
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
