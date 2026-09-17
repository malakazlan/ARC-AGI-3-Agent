"""Build `notebooks/submission.ipynb` from `agent/my_agent.py` and the `arc3/` package.

Cell layout (the pattern of Kaggle's official sample, "Stochastic Goose"):

  1. install the `arc-agi` wheel from the offline competition dataset
  2. create the bundle directories, then one `%%writefile` cell per arc3 module
     (readable in the notebook, so a failing daily run can still be inspected)
  3. write `my_agent.py` to /tmp (not /kaggle/working, so it never shows up as an output)
  4. in the competition rerun: wait for the gateway, copy the framework, register MyAgent,
     run `python main.py --agent myagent`
  5. otherwise write a dummy submission.parquet so save-and-run-all succeeds

`make notebook` runs this. Never hand-edit the notebook.
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

# ─────────────────────────────────────────────────────────────────────────────
# Kaggle accelerator: "cpu", "t4" (default, T4 x2), "p100", "rtx6000" (ARC-AGI-3 only).
# ─────────────────────────────────────────────────────────────────────────────
ACCELERATOR = "t4"

_ACCELERATORS = {
    "cpu":     {"name": "none",            "gpu": False},
    "t4":      {"name": "nvidiaTeslaT4",   "gpu": True},
    "p100":    {"name": "nvidiaTeslaP100", "gpu": True},
    "rtx6000": {"name": "nvidiaRtx6000",   "gpu": True},
}

ROOT = Path(__file__).resolve().parents[1]
AGENT_SRC = ROOT / "agent" / "my_agent.py"
PACKAGE_DIR = ROOT / "arc3"
NOTEBOOK_PATH = ROOT / "notebooks" / "submission.ipynb"
METADATA_PATH = ROOT / "notebooks" / "kernel-metadata.json"
BUNDLE_DIR = "/tmp/arc3_bundle"


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {"trusted": True},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def package_files() -> list[Path]:
    return sorted(p for p in PACKAGE_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def bundle_cells() -> list[dict]:
    files = package_files()
    dirs = sorted({(Path(BUNDLE_DIR) / f.relative_to(ROOT).parent).as_posix() for f in files})
    cells = [code_cell("!mkdir -p " + " ".join(dirs))]
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        cells.append(code_cell(f"%%writefile {BUNDLE_DIR}/{rel}\n" + path.read_text()))
    return cells


def build() -> dict:
    if not AGENT_SRC.exists():
        raise SystemExit(f"Could not find {AGENT_SRC}")
    if not package_files():
        raise SystemExit(f"No package files under {PACKAGE_DIR}")

    install_cell = code_cell(
        "!pip install --no-index --find-links \\\n"
        "    /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels \\\n"
        "    arc-agi python-dotenv"
    )

    write_agent_cell = code_cell("%%writefile /tmp/my_agent.py\n" + AGENT_SRC.read_text())

    run_cell = code_cell(dedent(
        f"""\
        import os

        if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
            # Wait for the gateway sidecar to be ready.
            !curl --fail --retry 999 --retry-all-errors --retry-delay 5 \\
                  --retry-max-time 600 http://gateway:8001/api/games

            # Copy the framework into a writable location.
            !cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents \\
                   /kaggle/working/ARC-AGI-3-Agents

            # Drop our agent in as a framework template.
            !cp /tmp/my_agent.py \\
                /kaggle/working/ARC-AGI-3-Agents/agents/templates/my_agent.py

            # Register MyAgent. The upstream __init__.py eagerly imports templates with
            # deps we don't ship (langgraph, smolagents, ...), so we replace it.
            with open('/kaggle/working/ARC-AGI-3-Agents/agents/__init__.py', 'w') as f:
                f.write(\"\"\"from typing import Type
        from dotenv import load_dotenv
        from .agent import Agent, Playback
        from .swarm import Swarm
        from .templates.random_agent import Random
        from .templates.my_agent import MyAgent

        load_dotenv()

        AVAILABLE_AGENTS: dict[str, Type[Agent]] = {{
            'random': Random,
            'myagent': MyAgent,
        }}
        \"\"\")

            # Point the framework at the gateway sidecar.
            with open('/kaggle/working/ARC-AGI-3-Agents/.env', 'w') as f:
                f.write(\"\"\"SCHEME=http
        HOST=gateway
        PORT=8001
        ARC_API_KEY=test-key-123
        ARC_BASE_URL=http://gateway:8001/
        OPERATION_MODE=online
        ENVIRONMENTS_DIR=
        RECORDINGS_DIR=/kaggle/working/server_recording
        \"\"\")

            # Run it. The gateway records every action and emits submission.parquet.
            !cd /kaggle/working/ARC-AGI-3-Agents && \\
                ARC3_BUNDLE_DIR={BUNDLE_DIR} MPLBACKEND=agg \\
                python main.py --agent myagent
        """
    ))

    dummy_submission_cell = code_cell(dedent(
        """\
        import os
        if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
            # Save-and-run-all (commit) mode: emit a dummy submission so the commit
            # succeeds. The real submission.parquet comes from the gateway in the rerun.
            import pandas as pd
            submission = pd.DataFrame(
                data=[['1_0', '1', True, 1]],
                columns=['row_id', 'game_id', 'end_of_game', 'score'])
            submission.to_parquet('/kaggle/working/submission.parquet', index=False)
            submission.head()
        """
    ))

    if ACCELERATOR not in _ACCELERATORS:
        raise SystemExit(f"Unknown ACCELERATOR={ACCELERATOR!r}. Pick one of: {sorted(_ACCELERATORS)}")
    accel = _ACCELERATORS[ACCELERATOR]

    return {
        "metadata": {
            "kernelspec": {"language": "python", "display_name": "Python 3", "name": "python3"},
            "language_info": {
                "name": "python",
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "pygments_lexer": "ipython3",
            },
            "kaggle": {
                "accelerator": accel["name"],
                "isInternetEnabled": False,
                "isGpuEnabled": accel["gpu"],
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat_minor": 4,
        "nbformat": 4,
        "cells": [
            markdown_cell(
                "# ARC Prize 2026 — ARC-AGI-3 Submission\n\n"
                "Built from `agent/my_agent.py` and `arc3/` via `scripts/build_notebook.py`. "
                "Do not edit cells directly — edit the source files and re-run `make notebook`."
            ),
            install_cell,
            *bundle_cells(),
            write_agent_cell,
            run_cell,
            dummy_submission_cell,
        ],
    }


def main() -> None:
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    notebook = build()
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1))
    print(f"[build_notebook] Wrote {NOTEBOOK_PATH.relative_to(ROOT)}  "
          f"({len(notebook['cells'])} cells, {len(package_files())} arc3 files, "
          f"accelerator: {ACCELERATOR})")

    # Keep notebooks/kernel-metadata.json in sync so flipping CPU/GPU is one edit.
    if METADATA_PATH.exists():
        meta = json.loads(METADATA_PATH.read_text())
        wanted = _ACCELERATORS[ACCELERATOR]["gpu"]
        if meta.get("enable_gpu") != wanted:
            meta["enable_gpu"] = wanted
            METADATA_PATH.write_text(json.dumps(meta, indent=2) + "\n")
            print(f"[build_notebook] Synced enable_gpu={wanted} in {METADATA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
