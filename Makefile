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
lint:  ## Parse and lint every workflow
	@command -v actionlint >/dev/null 2>&1 || \
		go install github.com/rhysd/actionlint/cmd/actionlint@$(ACTIONLINT_VERSION)
	@PATH="$$PATH:$$(go env GOPATH)/bin" actionlint -color

contract:  ## Reusable workflows are callable, and the README matches their inputs
	@python3 tools/check-workflows.py
