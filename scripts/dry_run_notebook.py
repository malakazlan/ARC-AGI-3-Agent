"""Offline dry run of the built Kaggle notebook.

Replays what Kaggle does, without Kaggle: executes the notebook's bundle and agent cells into
a scratch tree, starts the toolkit's own REST gateway locally in competition mode (the same
server Kaggle runs), copies the vendored framework the way the competition cell does, and runs
`python main.py --agent myagent` against that gateway with the repo deliberately off sys.path
so the agent must come from the bundle.

Checks: no online pip install, no URL but the gateway, main.py exits 0, one ARC3DIAG line per
game, no Traceback, scorecard produced.

    .venv/bin/python scripts/dry_run_notebook.py [--max-actions 150] [--games 3]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "submission.ipynb"
VENDOR = ROOT / "vendor" / "ARC-AGI-3-Agents"
WORK = Path("/tmp/arc3_dry_run")
PORT = 8011


def cells() -> list[str]:
    nb = json.loads(NOTEBOOK.read_text())
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def relocate(path: str) -> Path:
    """Map the notebook's absolute paths into the scratch tree."""
    return WORK / path.lstrip("/")


def run_static_cells(sources: list[str]) -> tuple[Path, Path, str]:
    """Execute pip (checked, not run), mkdir and %%writefile cells. Returns bundle dir, agent file, rerun cell."""
    bundle_dir = agent_file = None
    rerun = ""
    for src in sources:
        first = src.strip().splitlines()[0] if src.strip() else ""
        if "pip install" in src:
            assert "--no-index" in src, "pip install without --no-index"
            assert not re.search(r"https?://", src), "pip install references a URL"
            continue
        if first.startswith("!mkdir -p"):
            for p in first.split()[2:]:
                relocate(p).mkdir(parents=True, exist_ok=True)
                if p.startswith("/tmp/arc3_bundle") and bundle_dir is None:
                    bundle_dir = relocate("/tmp/arc3_bundle")
            continue
        if first.startswith("%%writefile"):
            target = relocate(first.split()[1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(src.split("\n", 1)[1])
            if target.name == "my_agent.py":
                agent_file = target
            continue
        if "KAGGLE_IS_COMPETITION_RERUN" in src and "main.py" in src:
            rerun = src
    assert bundle_dir and bundle_dir.exists(), "bundle dir not created"
    assert agent_file and agent_file.exists(), "my_agent.py not written"
    assert rerun, "competition rerun cell not found"
    for needle in ("cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents",
                   "agents/templates/my_agent.py", "python main.py --agent myagent", "http://gateway:8001"):
        assert needle in rerun, f"rerun cell lacks: {needle}"
    return bundle_dir, agent_file, rerun


def prepare_framework(agent_file: Path, rerun: str) -> Path:
    """Do what the rerun cell does, against localhost instead of the gateway host."""
    dest = relocate("/kaggle/working/ARC-AGI-3-Agents")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(VENDOR, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
    shutil.copy(agent_file, dest / "agents" / "templates" / "my_agent.py")
    init_body = re.search(r"agents/__init__\.py', 'w'\) as f:\n\s*f\.write\(\"\"\"(.*?)\"\"\"\)", rerun, re.S).group(1)
    (dest / "agents" / "__init__.py").write_text(init_body)
    env_body = re.search(r"\.env', 'w'\) as f:\n\s*f\.write\(\"\"\"(.*?)\"\"\"\)", rerun, re.S).group(1)
    env_body = env_body.replace("HOST=gateway", "HOST=localhost").replace("PORT=8001", f"PORT={PORT}")
    env_body = env_body.replace("http://gateway:8001/", f"http://localhost:{PORT}/")
    env_body = env_body.replace("RECORDINGS_DIR=/kaggle/working/server_recording",
                                f"RECORDINGS_DIR={relocate('/kaggle/working/server_recording')}")
    (dest / ".env").write_text(env_body)
    return dest


def start_gateway(games: int | None) -> subprocess.Popen:
    code = f"""
import logging, sys
sys.path.insert(0, {str(ROOT)!r})
import arc_agi
from arc_agi import OperationMode
logging.getLogger('werkzeug').setLevel(logging.ERROR)
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir={str(ROOT / 'environment_files')!r})
if {games!r} is not None:
    arc.available_environments = arc.available_environments[:{games!r}]
arc.listen_and_serve(host='127.0.0.1', port={PORT}, competition_mode=True)
"""
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/games", timeout=2) as r:
                n = len(json.loads(r.read()))
                print(f"[dry-run] gateway up with {n} games")
                return proc
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("gateway did not start")


def run_agent(framework: Path, bundle_dir: Path, max_actions: int) -> tuple[int, str, float]:
    env = dict(os.environ)
    env["ARC3_BUNDLE_DIR"] = str(bundle_dir)
    env["ARC3_CONFIG_JSON"] = json.dumps({"max_actions_per_game": max_actions, "global_budget_s": 1800})
    env["MPLBACKEND"] = "agg"
    env.pop("PYTHONPATH", None)
    started = time.time()
    proc = subprocess.run([sys.executable, "main.py", "--agent", "myagent"], cwd=framework, env=env,
                          capture_output=True, text=True, timeout=3600)
    return proc.returncode, proc.stdout + "\n" + proc.stderr, time.time() - started


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-actions", type=int, default=150)
    p.add_argument("--games", type=int, default=None, help="limit the roster (default: all cached)")
    args = p.parse_args()
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    sources = cells()
    urls = {u for s in sources for u in re.findall(r"https?://[^\s\"')]+", s)}
    assert all(u.startswith("http://gateway:8001") for u in urls), f"unexpected URLs: {urls}"
    bundle_dir, agent_file, rerun = run_static_cells(sources)
    print(f"[dry-run] {len(list(bundle_dir.rglob('*.py')))} bundled arc3 files, agent at {agent_file}")
    framework = prepare_framework(agent_file, rerun)

    gateway = start_gateway(args.games)
    try:
        code, output, wall = run_agent(framework, bundle_dir, args.max_actions)
    finally:
        gateway.kill()

    diag = [l for l in output.splitlines() if l.startswith("ARC3DIAG")]
    tracebacks = output.count("Traceback")
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/games", timeout=2) if False else open(os.devnull) as _:
        pass
    games_played = {json.loads(l.split(" ", 1)[1])["game_id"] for l in diag}
    levels = sum(json.loads(l.split(" ", 1)[1])["levels_completed"] for l in diag)
    fallbacks = sum(json.loads(l.split(" ", 1)[1])["fallbacks"] for l in diag)
    print(f"[dry-run] main.py exit={code} wall={wall:.0f}s games_with_diag={len(games_played)} "
          f"levels={levels} fallbacks={fallbacks} tracebacks={tracebacks}")
    (WORK / "main_output.log").write_text(output)
    ok = code == 0 and diag and tracebacks == 0 and fallbacks == 0
    print("[dry-run] PASS" if ok else "[dry-run] FAIL (see /tmp/arc3_dry_run/main_output.log)")
    if not ok:
        print(output[-3000:])
        sys.exit(1)


if __name__ == "__main__":
    main()
