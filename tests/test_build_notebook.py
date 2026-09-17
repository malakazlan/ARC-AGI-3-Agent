"""The Kaggle notebook must carry the arc3 package and stay offline."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_notebook():
    spec = importlib.util.spec_from_file_location("build_notebook", ROOT / "scripts" / "build_notebook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build()


def all_source(notebook) -> str:
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


def test_notebook_bundles_every_arc3_module():
    source = all_source(build_notebook())
    for path in (ROOT / "arc3").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        assert rel in source, f"{rel} not bundled"
    assert "def segment_objects" in source


def test_notebook_has_no_network_access_beyond_the_gateway():
    source = all_source(build_notebook())
    urls = set(re.findall(r"https?://[^\s\"')]+", source))
    assert all(u.startswith("http://gateway:8001") for u in urls), urls
    pip_lines = [l for l in source.splitlines() if "pip install" in l]
    assert all("--no-index" in l for l in pip_lines), pip_lines


def test_notebook_stays_off_the_internet_and_keeps_agent_out_of_outputs():
    notebook = build_notebook()
    assert notebook["metadata"]["kaggle"]["isInternetEnabled"] is False
    source = all_source(notebook)
    assert "%%writefile /kaggle/working/my_agent.py" not in source
