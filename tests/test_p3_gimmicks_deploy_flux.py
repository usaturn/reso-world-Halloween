"""S-criteria test for ``modeling/p3_gimmicks/deploy_flux.py`` (W10).

Why this test exists (create-reso-world AGENTS.md, test criterion S): the checked-in Flux manifest keeps its world state and
deploy state relative to the parent checkout. A deploy from a worktree rewrites them; if the rewrite pointed anywhere other
than the given ``.resoloop`` directory, resoloop would read another apply state or start a fresh deploy state inside the
worktree without an error, and the next deploy from the parent checkout would not know the module it replaced (the record
of the deployed module is lost). The project rules keep every state file in the parent checkout.
"""

from __future__ import annotations

from pathlib import Path

from modeling.p3_gimmicks import deploy_flux


def test_states_resolve_into_the_given_resoloop_directory(tmp_path: Path):
    doc = deploy_flux.resolved_manifest(tmp_path / ".resoloop")
    assert Path(doc["worldState"]) == tmp_path / ".resoloop" / "state" / "p2_A_plaza.json"
    assert Path(doc["deployState"]) == tmp_path / ".resoloop" / "flux-state" / "p3_plaza_dance.json"
    source = Path(doc["modules"][0]["source"])
    assert source.is_absolute() and source == deploy_flux.MANIFEST.parent / "P3PlazaDance.pg"
