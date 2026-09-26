.DEFAULT_GOAL := help
SHELL := /bin/bash

ACTIONLINT_VERSION := v1.7.7

.PHONY: help check lint contract

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

check: lint contract  ## Everything CI runs

# From source rather than the upstream install script: `go install` verifies against the
# module checksum database, and curl|bash verifies nothing. supply-chain-review.
#
# shellcheck is required, not optional. actionlint runs it over every `run:` block when
# it is present and silently skips that entire class of check when it is not — which is
# how this target first reported clean on a file CI then failed on. A local gate that is
# quietly weaker than CI is worse than no local gate.
lint:  ## Parse and lint every workflow
	@command -v shellcheck >/dev/null 2>&1 || { \
		echo "shellcheck is not installed — actionlint would skip every run: block."; \
		echo "  brew install shellcheck"; exit 1; }
	@command -v actionlint >/dev/null 2>&1 || \
		go install github.com/rhysd/actionlint/cmd/actionlint@$(ACTIONLINT_VERSION)
	@PATH="$$PATH:$$(go env GOPATH)/bin" actionlint -color

contract:  ## Reusable workflows are callable, and the README matches their inputs
	@python3 tools/check-workflows.py
