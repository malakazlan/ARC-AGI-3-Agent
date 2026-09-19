"""Track B harness: can a local vision-language model name a game's goal from frames + summary?

Offline only. Reads recorded traces, sends the last few frames of the first level plus our
world summary to an OpenAI-compatible endpoint (vLLM), parses the JSON answer and scores the
named template against eval/goal_truth.json. Without --endpoint it uses the MockClient, so the
whole pipeline runs with no network.

    .venv/bin/python eval/reasoner_eval.py --games ls20,cn04                    # dry run (mock)
    .venv/bin/python eval/reasoner_eval.py --endpoint http://host:8000 --model Qwen/Qwen2.5-VL-7B-Instruct
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arc3.perception import segment_objects  # noqa: E402
from arc3.reasoner.client import MockClient, VLLMClient  # noqa: E402
from arc3.reasoner.prompt import TEMPLATE_NAMES, build_messages, parse_answer  # noqa: E402
from arc3.reasoner.render import grid_to_png_b64  # noqa: E402
from arc3.reasoner.summary import world_summary  # noqa: E402
from eval.traces import Trace  # noqa: E402

DEFAULT_TRACES = ROOT / "experiments" / "2026-09-18-clickfx2-dev" / "traces"
DEFAULT_TRUTH = ROOT / "eval" / "goal_truth.json"
NAMED_WITHIN = 10
ANSWER_FIELDS = ("template", "goal", "progress", "next")


def query_steps(trace: Trace, steps: list[int]) -> list[int]:
    """Requested trace indices that exist and still lie inside the first level."""
    n = len(trace.levels)
    return [k for k in steps if 0 <= k < n and int(trace.levels[k]) == int(trace.levels[0])]


def frames_up_to(trace: Trace, k: int, frames: int) -> list[np.ndarray]:
    return [trace.grids[i] for i in range(max(0, k - frames + 1), k + 1)]


def summary_at(trace: Trace, k: int) -> str:
    """Summary from what the frames alone show: objects and level, nothing learned yet."""
    grid = trace.grids[k]
    return world_summary(grid, objects=segment_objects(grid), avatar_cells=None, key_vectors={},
                         tools={}, bar=None, deaths=0, level=int(trace.levels[k]),
                         templates=list(TEMPLATE_NAMES))


def run_query(client: Any, trace: Trace, k: int, frames: int, scale: int = 8) -> dict:
    pngs = [grid_to_png_b64(g, scale) for g in frames_up_to(trace, k, frames)]
    messages = build_messages(pngs, summary_at(trace, k))
    started = time.monotonic()
    try:
        raw = client.chat(messages)
        error = None
    except RuntimeError as exc:
        raw, error = "", str(exc)
    answer = parse_answer(raw) or {}
    record = {"game": trace.game_id, "step": int(k), "raw": raw, "error": error,
              "seconds": round(time.monotonic() - started, 2)}
    record.update({field: _as_text(answer.get(field)) for field in ANSWER_FIELDS})
    return record


def score_results(results: list[dict], truth: dict) -> dict:
    """Per game: template answers by step, named_within_10, first_correct_step; plus the fraction."""
    games: dict[str, dict] = {}
    for r in results:
        game = r["game"]
        if game not in truth:
            continue
        entry = games.setdefault(game, {"truth": truth[game]["template"], "answers": {},
                                        "named_within_10": False, "first_correct_step": None})
        entry["answers"][int(r["step"])] = r.get("template") or ""
    for entry in games.values():
        correct = sorted(s for s, t in entry["answers"].items() if t == entry["truth"])
        entry["first_correct_step"] = correct[0] if correct else None
        entry["named_within_10"] = any(s <= NAMED_WITHIN for s in correct)
    n = len(games)
    hits = sum(e["named_within_10"] for e in games.values())
    return {"games": games, "n_games": n, "named_within_10": hits,
            "fraction_named_within_10": hits / n if n else 0.0}


def format_table(score: dict, steps: list[int]) -> str:
    head = f"{'game':6} {'truth':14} " + " ".join(f"{'s' + str(s):>14}" for s in steps) + f" {'named<=10':>9}"
    lines = [head]
    for game, e in sorted(score["games"].items()):
        cells = " ".join(f"{(e['answers'].get(s) or '-')[:14]:>14}" for s in steps)
        lines.append(f"{game:6} {e['truth']:14} {cells} {'yes' if e['named_within_10'] else 'no':>9}")
    lines.append(f"named within {NAMED_WITHIN}: {score['named_within_10']}/{score['n_games']} "
                 f"= {100 * score['fraction_named_within_10']:.0f}%")
    return "\n".join(lines)


def trace_files(folder: Path, games: list[str] | None) -> list[Path]:
    paths = sorted(folder.glob("*_s0.npz"))
    if games:
        paths = [p for p in paths if p.name.split("_")[0] in games]
    return paths


def make_client(endpoint: str | None, model: str, timeout_s: float) -> Any:
    return MockClient() if not endpoint else VLLMClient(endpoint, model, timeout_s)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--traces", type=Path, default=DEFAULT_TRACES)
    p.add_argument("--endpoint", default=None, help="http://host:8000; omit for the MockClient")
    p.add_argument("--model", default="mock")
    p.add_argument("--steps", default="0,3,6,10", help="trace indices in the first level to query")
    p.add_argument("--frames", type=int, default=3, help="recent frames sent per query")
    p.add_argument("--scale", type=int, default=8, help="pixels per cell in the PNG")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    p.add_argument("--out", type=Path, default=None, help="default eval/results/reasoner_<model>.json")
    p.add_argument("--games", default=None, help="comma-separated game ids")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    steps = [int(s) for s in args.steps.split(",") if s.strip()]
    games = [g.strip() for g in args.games.split(",")] if args.games else None
    truth = json.loads(Path(args.truth).read_text())
    client = make_client(args.endpoint, args.model, args.timeout)
    paths = trace_files(Path(args.traces), games)
    if not paths:
        raise SystemExit(f"no *_s0.npz traces under {args.traces}")
    results: list[dict] = []
    for path in paths:
        trace = Trace.load(path)
        for k in query_steps(trace, steps):
            results.append(run_query(client, trace, k, args.frames, args.scale))
    score = score_results(results, truth)
    print(format_table(score, steps))
    out = args.out or ROOT / "eval" / "results" / f"reasoner_{args.model.replace('/', '_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": args.model, "endpoint": args.endpoint, "steps": steps,
                               "frames": args.frames, "results": results, "score": score}, indent=1))
    print(f"wrote {out}")
    return 0


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
