SHELL := /bin/bash
TOOLS_DIR ?= $(CURDIR)/.local/bin
export TOOLS_DIR
BUILD_CA_BUNDLE ?= $(CURDIR)/.local/build-ca.pem
export BUILD_CA_BUNDLE
export PATH := $(CURDIR)/.local/venv/bin:$(TOOLS_DIR):$(PATH)
export PYTHONPATH := app

.PHONY: tools unit validate compose-up compose-check compose-down gitops-up gitops-check gitops-down scan sbom

tools:
	python scripts/install-lab-tools.py
	python -m venv .local/venv
	.local/venv/bin/pip install -r app/requirements.txt -r tests/requirements.txt

unit:
	python -m unittest discover -s app/tests -v
	python -m unittest discover -s tests -v

validate: unit
	docker compose config --quiet
	kubectl kustomize deploy/overlays/local > /dev/null
	python -c 'from pathlib import Path; import yaml; [list(yaml.safe_load_all(p.read_text())) for p in Path("platform/rollouts").glob("*.yaml")]'
	docker compose -f compose.yaml -f compose.gitops.yaml -f compose.rollouts.yaml config --quiet

.PHONY: prepare-build-ca
prepare-build-ca:
	mkdir -p .local
	@if [ "$(BUILD_CA_BUNDLE)" = "$(CURDIR)/.local/build-ca.pem" ]; then cp /etc/ssl/certs/ca-certificates.crt "$(BUILD_CA_BUNDLE)"; fi

compose-up: prepare-build-ca
	chmod -R a+rX observability
	docker compose up -d --build

compose-check:
	python scripts/smoke-observability.py --output .local/compose-evidence.json

compose-down:
	docker compose down --volumes --remove-orphans

gitops-up: prepare-build-ca
	chmod -R a+rX observability
	docker compose build app
	python scripts/gitops-up.py

gitops-check:
	python scripts/gitops-check.py

gitops-down:
	docker compose -f compose.yaml -f compose.gitops.yaml down --volumes --remove-orphans
	kind delete cluster --name portfolio
	@if docker network ls --format '{{.Name}}' | grep -qx portfolio-kind; then docker network rm portfolio-kind; fi
	@rm -f .local/kubeconfig

scan:
	mkdir -p .local
	trivy image --scanners vuln,secret --severity HIGH,CRITICAL --exit-code 1 --format json --output .local/trivy.json portfolio-api:v1

sbom:
	mkdir -p .local
	syft portfolio-api:v1 -o spdx-json=.local/sbom.spdx.json

.PHONY: rollouts-up rollouts-check rollouts-down
rollouts-up:
	python scripts/rollouts-up.py

rollouts-check:
	python scripts/rollouts-check.py

# Remove only this optional lab; keep the existing platform available.
rollouts-down:
	@test "$$(KUBECONFIG=$(CURDIR)/.local/kubeconfig kubectl config current-context)" = kind-portfolio
	KUBECONFIG=$(CURDIR)/.local/kubeconfig kubectl delete namespace progressive-delivery argo-rollouts --ignore-not-found
	docker compose -f compose.yaml -f compose.gitops.yaml up -d --remove-orphans
