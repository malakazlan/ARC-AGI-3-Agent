"""Track B pieces on synthetic data: summary text, prompt shape and parser, PNG writer, clients,
and the harness scorer. No network, no game engine."""
from __future__ import annotations

import base64
import json

import numpy as np

from arc3.perception import segment_objects
from arc3.reasoner.client import MockClient, VLLMClient
from arc3.reasoner.prompt import TEMPLATE_NAMES, build_messages, parse_answer
from arc3.reasoner.render import PALETTE, PNG_SIGNATURE, grid_to_png, grid_to_png_b64, png_size
from arc3.reasoner.summary import MAX_CHARS, world_summary
from eval.reasoner_eval import format_table, query_steps, score_results


def toy_grid() -> np.ndarray:
    g = np.zeros((16, 16), dtype=np.int8)
    g[2:4, 2:4] = 3      # a 2x2 block
    g[10, 5:9] = 9       # a bar of 4
    g[7, 7] = 12         # a single cell
    return g


def summary_of(grid: np.ndarray, **overrides) -> str:
    kwargs = dict(objects=segment_objects(grid), avatar_cells={(2, 2), (2, 3), (3, 2), (3, 3)},
                  key_vectors={1: (-5, 0), 2: (5, 0)}, tools={(3,): "dial"},
                  bar={"capacity": 20, "remaining": 12, "rate": 1}, deaths=1, level=0,
                  templates=list(TEMPLATE_NAMES))
    kwargs.update(overrides)
    return world_summary(grid, **kwargs)


# --- summary ---------------------------------------------------------------------------------

def test_summary_names_grid_objects_avatar_keys_tools_bar_templates():
    text = summary_of(toy_grid())
    assert "16x16" in text and "3 objects" in text
    assert "colour 9, size 4, at (10, 5)" in text
    assert "Avatar: 4 cells, top-left at (2, 2)" in text
    assert "Key 1 moves the avatar by (-5, 0)" in text and "Key 2 moves the avatar by (5, 0)" in text
    assert "Touching colour 3 does dial" in text
    assert "capacity 20, remaining 12, rate 1" in text
    assert "Deaths so far: 1" in text
    for name in TEMPLATE_NAMES:
        assert name in text


def test_summary_handles_unknowns_and_stays_short():
    g = np.zeros((64, 64), dtype=np.int8)
    g[::2, ::2] = 5  # 1024 single-cell objects
    text = summary_of(g, avatar_cells=None, key_vectors={}, tools={}, bar=None, deaths=0)
    assert "Avatar: unknown" in text
    assert "+1016 more" in text
    assert "Energy bar" not in text
    assert len(text) <= MAX_CHARS


# --- prompt ----------------------------------------------------------------------------------

def test_build_messages_shape():
    messages = build_messages(["AAAA", "BBBB"], "summary text")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "goal" in messages[0]["content"].lower()
    images = [p for p in messages[1]["content"] if p["type"] == "image_url"]
    assert len(images) == 2
    assert images[0]["image_url"]["url"] == "data:image/png;base64,AAAA"
    texts = " ".join(p["text"] for p in messages[1]["content"] if p["type"] == "text")
    assert "summary text" in texts and '"template"' in texts and "other" in texts


def test_parse_answer_fenced_json():
    text = 'Sure.\n```json\n{"template": "reach", "goal": "go", "progress": "d", "next": "n"}\n```'
    assert parse_answer(text)["template"] == "reach"


def test_parse_answer_prose_wrapped_json():
    text = 'I think {"template": "collect", "goal": "x {nested}", "n": 1} is right.'
    assert parse_answer(text) == {"template": "collect", "goal": "x {nested}", "n": 1}


def test_parse_answer_garbage_is_none():
    assert parse_answer("no json here { broken") is None
    assert parse_answer("") is None
    assert parse_answer("[1, 2, 3]") is None


# --- render ----------------------------------------------------------------------------------

def test_png_signature_and_dimensions():
    data = grid_to_png(np.zeros((64, 64), dtype=np.int8), scale=8)
    assert data[:8] == PNG_SIGNATURE
    assert png_size(data) == (512, 512)
    assert data[-12:-8] == b"\x00\x00\x00\x00" and data[-8:-4] == b"IEND"


def test_png_b64_decodes_and_palette_is_sixteen_colours():
    b64 = grid_to_png_b64(np.full((4, 6), 15, dtype=np.int8), scale=2)
    data = base64.b64decode(b64, validate=True)
    assert png_size(data) == (12, 8)
    assert len(PALETTE) == 16 and all(len(c) == 3 for c in PALETTE)


def test_png_out_of_range_values_are_clipped():
    g = np.array([[-1, 99]], dtype=np.int16)
    assert png_size(grid_to_png(g, scale=1)) == (2, 1)


# --- clients ---------------------------------------------------------------------------------

def test_mock_client_returns_fixed_json_and_counts_calls():
    client = MockClient()
    text = client.chat(build_messages([], "s"))
    assert json.loads(text)["template"] == "reach"
    custom = MockClient({"template": "other", "goal": "?", "progress": "?", "next": "?"})
    assert json.loads(custom.chat([]))["template"] == "other"
    assert len(client.calls) == 1 and len(custom.calls) == 1


def test_vllm_client_normalises_base_url():
    client = VLLMClient("http://localhost:8000/", "m")
    assert client.base_url == "http://localhost:8000" and client.model == "m"


# --- harness ---------------------------------------------------------------------------------

def test_score_results_named_within_10_and_first_correct_step():
    truth = {"a": {"template": "reach", "note": ""}, "b": {"template": "match_display", "note": ""},
             "c": {"template": "other", "note": ""}}
    results = [
        {"game": "a", "step": 0, "template": "other"},
        {"game": "a", "step": 6, "template": "reach"},
        {"game": "b", "step": 0, "template": "reach"},
        {"game": "b", "step": 12, "template": "match_display"},  # correct, but too late
        {"game": "zz", "step": 0, "template": "reach"},  # no truth: ignored
    ]
    score = score_results(results, truth)
    assert score["n_games"] == 2 and score["named_within_10"] == 1
    assert score["games"]["a"]["first_correct_step"] == 6 and score["games"]["a"]["named_within_10"]
    assert score["games"]["b"]["first_correct_step"] == 12 and not score["games"]["b"]["named_within_10"]
    assert abs(score["fraction_named_within_10"] - 0.5) < 1e-9
    table = format_table(score, [0, 6, 12])
    assert "a      reach" in table and "1/2 = 50%" in table


def test_query_steps_stay_inside_first_level():
    from eval.traces import Trace
    n = 8
    trace = Trace("toy", 0, np.zeros((n, 4, 4), dtype=np.int8), np.zeros(n, dtype=np.int16),
                  np.full(n, -1, dtype=np.int16), np.full(n, -1, dtype=np.int16),
                  np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int16),
                  np.array(["NOT_FINISHED"] * n), np.ones(n, dtype=np.int16))
    assert query_steps(trace, [0, 3, 6, 10]) == [0, 3]
