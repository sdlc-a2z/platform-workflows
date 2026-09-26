#!/usr/bin/env python3
"""Check that the reusable workflows here are callable, and that the README still
describes them accurately.

`actionlint` already covers whether a workflow parses and whether its expressions
resolve against the contexts available. Two things it cannot know matter here:

  * A workflow in this repository exists to be *called*. One that forgets
    `on: workflow_call` is not reusable, and the caller's error does not say so.

  * Eleven repositories copy their call block out of the README. Rename an input, or add
    a required one, and every caller breaks while the README goes on showing the old
    shape. Nothing fails until someone pushes, and then it fails in their repository
    rather than this one.

Both are silent. That is the whole reason this file exists rather than a lint alone.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
README = ROOT / "README.md"

# This repository's own CI is not a reusable workflow and is not documented in the README.
NOT_REUSABLE = {"ci.yml"}

USES = re.compile(
    r"^sdlc-a2z/platform-workflows/\.github/workflows/(?P<file>[\w.-]+\.ya?ml)@(?P<ref>.+)$"
)


def on_block(doc: dict) -> dict:
    """The `on:` mapping.

    PyYAML follows YAML 1.1, where a bare `on` key is the boolean True. Every workflow in
    this repository therefore parses with a `True` key and no `"on"` key, which is a
    reliable way to write a checker that passes by finding nothing.
    """
    for key in ("on", True):
        value = doc.get(key)
        if isinstance(value, dict):
            return value
    return {}


def declared_inputs(doc: dict) -> tuple[dict, set[str]]:
    """(all inputs, those a caller must supply)."""
    call = on_block(doc).get("workflow_call") or {}
    inputs = call.get("inputs") or {}
    required = {
        name
        for name, spec in inputs.items()
        if isinstance(spec, dict) and spec.get("required") and "default" not in spec
    }
    return inputs, required


def find_calls(node, out: list[dict]) -> None:
    """Every mapping in a parsed README example whose `uses:` points back at this repo."""
    if isinstance(node, dict):
        uses = node.get("uses")
        if isinstance(uses, str) and USES.match(uses.strip()):
            out.append(node)
        for value in node.values():
            find_calls(value, out)
    elif isinstance(node, list):
        for value in node:
            find_calls(value, out)


def readme_examples() -> list[dict]:
    """Call blocks from the README's ```yaml fences.

    Fences that are not valid YAML are skipped rather than reported: the README also
    carries fragments that are deliberately incomplete.
    """
    calls: list[dict] = []
    for fence in re.findall(r"```ya?ml\n(.*?)```", README.read_text(), re.S):
        try:
            doc = yaml.safe_load(fence)
        except yaml.YAMLError:
            continue
        find_calls(doc, calls)
    return calls


def main() -> int:
    errors: list[str] = []

    workflows = sorted(p for p in WORKFLOWS.glob("*.yml") if p.name not in NOT_REUSABLE)
    if not workflows:
        print("no reusable workflows found — has the directory moved?", file=sys.stderr)
        return 1

    parsed: dict[str, dict] = {}
    for path in workflows:
        doc = yaml.safe_load(path.read_text())
        parsed[path.name] = doc
        if "workflow_call" not in on_block(doc):
            errors.append(
                f"{path.name}: no `on: workflow_call` — this repository exists to be "
                f"called, and a caller's error will not say this is why"
            )

    documented: set[str] = set()
    for call in readme_examples():
        match = USES.match(call["uses"].strip())
        assert match  # find_calls only collects matches
        name = match.group("file")
        documented.add(name)

        if name not in parsed:
            errors.append(f"README calls `{name}`, which does not exist here")
            continue

        # `@main` is a standing grant: every future commit here would run inside the
        # caller with whatever secrets it inherits. The README says to pin; it should
        # not then show an unpinned example.
        if match.group("ref") == "main":
            errors.append(f"README shows `{name}@main` — pin the example to a tag")

        # A block whose only key is `uses` is illustrating the reference itself — the
        # "Pin the version you call" fragment — not showing a caller how to call it.
        # Checking its inputs would demand a `with:` on a line that is about the tag.
        if set(call) == {"uses"}:
            continue

        inputs, required = declared_inputs(parsed[name])
        supplied = set((call.get("with") or {}).keys())

        for missing in sorted(required - supplied):
            errors.append(
                f"README example for `{name}` omits required input `{missing}` — "
                f"copying it gives a caller a workflow that cannot start"
            )
        for unknown in sorted(supplied - set(inputs)):
            errors.append(
                f"README example for `{name}` passes `{unknown}`, which it does not "
                f"declare — renamed or removed, and the README was not updated"
            )

    for name in parsed:
        if name not in documented:
            errors.append(
                f"{name} is not shown in the README — callers copy their call block "
                f"from there, so an undocumented workflow is an unused one"
            )

    if errors:
        print("workflows and README disagree:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(
        f"{len(parsed)} reusable workflows, all callable and all documented; "
        f"every README example matches its inputs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
