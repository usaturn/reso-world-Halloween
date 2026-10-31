"""W09R (S): ``hide_placeholders`` stops drawing only the replaced placeholder visual.

Damage prevented: the district declaration is re-applied by every later child. If the step disabled the renderer of
another Slot (a sibling, an attachment marker, an object outside the replacement range), that object would silently
vanish from the world with no error; the guard refuses a hide target outside ``visual_root``.
"""

from __future__ import annotations

import pytest

from modeling.p2_meshy import replacements


def node(name: str, renderer: bool = True, children: list | None = None) -> dict:
    comps = [{"key": f"mesh_{name}", "type": "FrooxEngine.StaticMesh", "fields": {"URL": f"$asset:mesh_{name}"}}]
    if renderer:
        comps.append({"key": f"renderer_{name}", "type": "FrooxEngine.MeshRenderer", "fields": {"Mesh": f"$component:mesh_{name}"}})
    return {"slot": {"name": name, "key": f"object_{name}"}, "components": comps, "children": children or []}


def district() -> dict:
    body = node("Proxy_Body", children=[node("Proxy_EyeAttach")])
    asset = {"slot": {"name": "Proxy", "key": "object_Proxy"}, "components": [], "children": [body, node("Proxy_Other")]}
    return {"slot": {"name": "D", "key": "root"}, "components": [], "children": [asset, node("Proxy_Body_FixedCollision", renderer=False)]}


def renderer_fields(doc: dict, name: str) -> dict:
    stack = [doc]
    while stack:
        n = stack.pop()
        if n["slot"]["name"] == name:
            return next(c["fields"] for c in n["components"] if c["type"] == "FrooxEngine.MeshRenderer")
        stack.extend(n.get("children", []))
    raise KeyError(name)


def test_only_the_configured_visual_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    rep = {"district": "D", "visual_root": "Proxy_Body", "hide": ["Proxy_Body"]}
    monkeypatch.setattr(replacements, "REPLACEMENTS", {"MX": rep})
    doc = district()
    rows = replacements.hide_placeholders(doc, "D")
    assert [r["slot"] for r in rows] == ["D/Proxy/Proxy_Body"]
    assert renderer_fields(doc, "Proxy_Body")["Enabled"] is False
    for other in ("Proxy_EyeAttach", "Proxy_Other"):
        assert "Enabled" not in renderer_fields(doc, other)
    assert replacements.hide_placeholders(district(), "E") == []  # other districts are untouched


def test_hide_target_outside_the_replacement_range_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    rep = {"district": "D", "visual_root": "Proxy_Body", "hide": ["Proxy_Other"]}
    monkeypatch.setattr(replacements, "REPLACEMENTS", {"MX": rep})
    with pytest.raises(ValueError, match="outside the replacement range"):
        replacements.hide_placeholders(district(), "D")
