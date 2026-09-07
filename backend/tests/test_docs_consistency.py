"""Guards against the exact drift that happened once already: the frontend
sidebar's Phase N string silently fell behind docs/roadmap.md for 11 phases
(39 -> 50) before anyone noticed. No network/DB access - pure text checks
against the repo's own files.

Skips (not fails) when docs/ or frontend/ aren't present next to this repo
checkout - Jenkins's Test stage runs pytest *inside the built backend Docker
image*, whose build context is backend/ alone (docker-compose.yml: `build:
./backend`), so neither sibling directory exists in that container at all.
This test is only meaningful against a full repo checkout (e.g. a plain
local `pytest` run, or a future CI stage that actually mounts the full
repo) - confirmed live 2026-09-07 after it crashed Jenkins build #146 with
FileNotFoundError for the very reason above.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROADMAP_PATH = REPO_ROOT / "docs" / "roadmap.md"
APP_TSX_PATH = REPO_ROOT / "frontend" / "src" / "App.tsx"


def _highest_roadmap_phase() -> int:
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^##\s+Phase\s+(\d+)", text, re.MULTILINE)]
    assert numbers, "no '## Phase N' headings found in docs/roadmap.md"
    return max(numbers)


def _sidebar_phase() -> int:
    text = APP_TSX_PATH.read_text(encoding="utf-8")
    match = re.search(r"Phase\s+(\d+)", text)
    assert match, "no 'Phase N' string found in frontend/src/App.tsx"
    return int(match.group(1))


@pytest.mark.skipif(
    not (ROADMAP_PATH.exists() and APP_TSX_PATH.exists()),
    reason="docs/ and frontend/ are outside the backend Docker build context - "
    "only present on a full repo checkout, not in Jenkins's containerized Test stage",
)
def test_sidebar_phase_matches_roadmap_latest():
    roadmap_phase = _highest_roadmap_phase()
    sidebar_phase = _sidebar_phase()
    assert sidebar_phase == roadmap_phase, (
        f"frontend/src/App.tsx shows 'Phase {sidebar_phase}' but "
        f"docs/roadmap.md's latest entry is Phase {roadmap_phase} - "
        "bump the sidebar string (or the roadmap, if the sidebar was updated first)."
    )
