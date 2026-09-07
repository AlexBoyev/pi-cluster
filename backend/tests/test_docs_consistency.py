"""Guards against the exact drift that happened once already: the frontend
sidebar's Phase N string silently fell behind docs/roadmap.md for 11 phases
(39 -> 50) before anyone noticed. No network/DB access - pure text checks
against the repo's own files.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _highest_roadmap_phase() -> int:
    text = (REPO_ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^##\s+Phase\s+(\d+)", text, re.MULTILINE)]
    assert numbers, "no '## Phase N' headings found in docs/roadmap.md"
    return max(numbers)


def _sidebar_phase() -> int:
    text = (REPO_ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    match = re.search(r"Phase\s+(\d+)", text)
    assert match, "no 'Phase N' string found in frontend/src/App.tsx"
    return int(match.group(1))


def test_sidebar_phase_matches_roadmap_latest():
    roadmap_phase = _highest_roadmap_phase()
    sidebar_phase = _sidebar_phase()
    assert sidebar_phase == roadmap_phase, (
        f"frontend/src/App.tsx shows 'Phase {sidebar_phase}' but "
        f"docs/roadmap.md's latest entry is Phase {roadmap_phase} - "
        "bump the sidebar string (or the roadmap, if the sidebar was updated first)."
    )
