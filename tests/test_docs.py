import ast
from pathlib import Path

import filament as fl


def test_every_public_export_is_present_in_api_reference():
    reference = Path("docs/api.md").read_text(encoding="utf-8")
    missing = [name for name in fl.__all__ if "`{}`".format(name) not in reference]
    assert not missing, "undocumented public exports: {}".format(", ".join(missing))


def test_reference_states_native_support_boundary():
    reference = Path("docs/api.md").read_text(encoding="utf-8")
    assert "## Support boundary" in reference
    assert "Python-side" in reference
    assert "does not parse the file" in reference


def test_type_stub_covers_every_public_export():
    tree = ast.parse(Path("src/filament/__init__.pyi").read_text(encoding="utf-8"))
    declared = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    declared.update(
        node.target.id for node in tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )
    assert set(fl.__all__) <= declared
