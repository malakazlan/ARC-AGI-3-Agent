# Track B runbook: goal naming by a local vision model (one pod session)

Purpose: one number per dev game, "did the model name the goal template within the first
10 actions?", for a model that could ship inside the Kaggle notebook. Decision rule in
`docs/DESIGN_V2.md` section 13: 50% or more, wire it as the level-1 fallback with our
planner executing; under 30%, drop the LLM path.

Everything below the pod line has already run end to end on the dev machine against the
mock client (`make reasoner-dry`), so the pod only pays for model time.

## What the pod needs

- One GPU with 40 GB or more (A100/H100). 24 GB is enough for the 8B model only.
- Docker with the vLLM OpenAI-compatible server image, Python 3.12 with numpy for the harness.
- This repo (a `git clone` is enough) and the recorded dev traces:
  `experiments/2026-09-18-clickfx2-dev/traces/*_s0.npz` (18 files). Copy them to the same
  path on the pod, or point `--traces` at wherever they land.
- Model weights, pulled on the pod (fast network). Licence rule from CLAUDE.md: permissive
  only; the Qwen line is Apache-2.0. Verify the exact repository ids on Hugging Face at pull
  time; the intent is:
  - smoke and fallback: Qwen3-VL-8B-Instruct
  - decisive run: Qwen3-VL-32B-Instruct, AWQ or FP8 build (fits an RTX 6000 24 GB at 4-bit,
    which is what Kaggle offers)

## Commands

Start the server (one model at a time; replace MODEL with the repository id):

```
docker run --gpus all --rm -p 8000:8000 --ipc=host \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model MODEL --max-model-len 8192 --limit-mm-per-prompt image=3 --dtype auto
```

Wait until `curl http://localhost:8000/v1/models` lists the model. Then, from the repo root:

```
python eval/reasoner_eval.py --endpoint http://localhost:8000 --model MODEL \
  --traces experiments/2026-09-18-clickfx2-dev/traces \
  --out eval/results/reasoner_$(basename MODEL).json
```

Expected size: 18 games x 4 query steps = 72 calls, 3 frames each. Minutes, not hours.
Do the 8B first (proves the pipeline against a real server), then the 32B.

## What to send back

The two files under `eval/results/` and the table the harness prints. Nothing else is needed.
If the server rejects the request, send the first 30 lines of the server log.

## What the harness does and does not do

- Sends the last 3 frames as PNG plus a short text summary of what is visible (objects,
  avatar position if any, level number, the list of our goal templates). At this stage it
  deliberately sends no learned effects: the question is whether the model can name the goal
  from what a player sees in the first 10 actions.
- Asks for JSON: template, goal sentence, progress signal, next sub-goal. Never actions.
- Scores template equality against `eval/goal_truth.json` (from the VISTA guides and the
  owner's play notes). The free-text goal is kept in the results file for a manual read.

## Kaggle fit (why this run decides anything)

Kaggle GPUs: T4 x2, P100, RTX 6000 (24 GB). A 32B model at 4-bit is about 18 GB plus
context; 10 to 30 calls per game at a few seconds each fits the 6-hour budget for 100+ games
only if calls happen at decision points (no goal yet, or stuck), which is how the agent would
use it. If the 32B is too slow on Kaggle hardware, the 8B is the shipping candidate, so its
number matters too.
