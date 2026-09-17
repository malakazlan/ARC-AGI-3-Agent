#!/usr/bin/env bash
# Bootstrap a fresh Linux box (Colab, a GPU pod, a CI runner) and run the benchmark.
#
# Colab:   !git clone https://github.com/malakazlan/ARC-AGI-3-Agent.git && \
#          !bash ARC-AGI-3-Agent/scripts/pod_bench.sh
# Pod:     bash scripts/pod_bench.sh            (from a checkout)
#
# Env knobs (all optional):
#   SPLIT=dev|holdout   which split to benchmark (default dev)
#   SEEDS=3             seeds per game (default 3)
#   BRANCH=main         branch to check out when cloning
#   REPO_URL=...        where to clone from when not already inside a checkout
#   SKIP_SETUP=1        reuse an existing .venv
#
# Output: experiments/<id>/results.json plus a summary on stdout. Copy the experiments/
# folder back into the repo and commit it; nothing else on the box matters.
set -euo pipefail

SPLIT="${SPLIT:-dev}"
SEEDS="${SEEDS:-3}"
BRANCH="${BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/malakazlan/ARC-AGI-3-Agent.git}"

# 1. Find or create the checkout.
if [ -f Makefile ] && [ -d agent ]; then
    ROOT="$(pwd)"
elif [ -f "$(dirname "$0")/../Makefile" ]; then
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
else
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" ARC-AGI-3-Agent
    ROOT="$(pwd)/ARC-AGI-3-Agent"
fi
cd "$ROOT"
echo "[pod_bench] repo: $ROOT ($(git rev-parse --short HEAD 2>/dev/null || echo 'no git'))"

# 2. System tools. Only when missing, and only if we can (root or sudo).
need=()
for tool in make git curl; do command -v "$tool" >/dev/null || need+=("$tool"); done
if [ "${#need[@]}" -gt 0 ]; then
    SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update -qq && $SUDO apt-get install -y -qq "${need[@]}"
fi

# 3. Python 3.12 via uv when the box lacks it (Colab ships 3.11/3.12, pods vary).
if ! command -v python3.12 >/dev/null; then
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    uv python install 3.12
fi
echo "[pod_bench] python3.12: $(python3.12 --version)"

# 4. Project setup (venv, pinned deps, vendored framework).
if [ "${SKIP_SETUP:-0}" != "1" ] || [ ! -d .venv ]; then
    make setup
fi

# 5. Run. The bench target lands in Phase 3; until then fall back to play-local.
if grep -qE '^bench:' Makefile; then
    make bench SPLIT="$SPLIT" SEEDS="$SEEDS"
else
    echo "[pod_bench] no bench target yet; running play-local"
    make play-local
fi

echo "[pod_bench] done. Results (if any):"
ls -1dt experiments/*/ 2>/dev/null | head -3 || true
