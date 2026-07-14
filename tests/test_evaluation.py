"""Tests for the model evaluation pipeline (TASK-011)."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from finetuning.evaluate import (
    EvalSample,
    compute_ragas_metrics,
    compute_text_metrics,
    generate_answers,
    generate_comparison_chart,
    load_eval_config,
    run_evaluation,
)

TINY_TEST_MODEL = "sshleifer/tiny-gpt2"
"""Lightweight model for fast CI inference."""


@pytest.fixture
def eval_config_path(tmp_path: Path) -> str:
    """Create a minimal evaluation config file."""
    config = [
        {
            "query": "What is Hermes?",
            "ground_truth": "Hermes is an AI research platform.",
            "context": "Hermes is a multi-agent AI research and retrieval platform.",
        },
        {
            "query": "What search does Hermes use?",
            "ground_truth": "Hermes uses hybrid BM25 and vector search.",
            "context": "Hermes combines BM25 keyword search with vector similarity.",
        },
    ]
    path = str(tmp_path / "eval_config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return path


@pytest.fixture
def eval_output_dir() -> Generator[str]:
    """Create and tear down a temporary output directory."""
    d = "tests/temp_evaluation"
    os.makedirs(d, exist_ok=True)
    yield d
    if os.path.exists(d):
        shutil.rmtree(d)


def test_load_eval_config(eval_config_path: str) -> None:
    """Validates JSON parsing and schema enforcement."""
    samples = load_eval_config(eval_config_path)

    assert len(samples) == 2
    assert isinstance(samples[0], EvalSample)
    assert samples[0].query == "What is Hermes?"
    assert samples[0].ground_truth == "Hermes is an AI research platform."
    assert samples[0].context != ""


def test_load_eval_config_missing_keys(tmp_path: Path) -> None:
    """Asserts ValueError when required keys are missing."""
    bad_config = [{"query": "Test?"}]
    path = str(tmp_path / "bad_config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bad_config, f)

    with pytest.raises(ValueError, match="missing keys"):
        load_eval_config(path)


def test_compute_text_metrics() -> None:
    """Feeds known prediction/reference pairs and asserts valid ROUGE/BLEU/BERTScore."""
    predictions = [
        "Hermes is an AI research platform for documents.",
        "Hermes uses hybrid search combining BM25 and vectors.",
    ]
    references = [
        "Hermes is an AI research platform.",
        "Hermes uses hybrid BM25 and vector search.",
    ]

    metrics = compute_text_metrics(predictions, references)

    assert "rouge1" in metrics
    assert "rouge2" in metrics
    assert "rougeL" in metrics
    assert "bleu" in metrics
    assert "bertscore_f1" in metrics

    for key, value in metrics.items():
        assert isinstance(value, float), f"{key} is not a float"
        assert 0.0 <= value <= 1.0, f"{key}={value} is out of range [0, 1]"

    assert metrics["rouge1"] > 0.3


def test_compute_ragas_metrics_no_api_key() -> None:
    """RAGAS metrics should return empty dict when no OPENAI_API_KEY is set."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        result = compute_ragas_metrics(
            queries=["What is Hermes?"],
            answers=["An AI platform."],
            contexts=["Hermes is a platform."],
            ground_truths=["Hermes is an AI platform."],
        )
    assert result == {}


def test_generate_answers() -> None:
    """Uses a tiny test model to verify inference returns non-empty strings."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(TINY_TEST_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        TINY_TEST_MODEL, torch_dtype=torch.float32, device_map={"": "cpu"}
    )

    samples = [
        EvalSample(
            query="What is Hermes?",
            ground_truth="An AI platform.",
            context="Hermes is a platform.",
        ),
    ]

    answers = generate_answers(model, tokenizer, samples, max_new_tokens=20)

    assert len(answers) == 1
    assert isinstance(answers[0], str)
    assert len(answers[0]) > 0


def test_generate_comparison_chart(eval_output_dir: str) -> None:
    """Verifies that a PNG chart file is created."""
    base_metrics = {"rouge1": 0.45, "bleu": 0.3, "bertscore_f1": 0.7}
    ft_metrics = {"rouge1": 0.65, "bleu": 0.5, "bertscore_f1": 0.85}
    chart_path = os.path.join(eval_output_dir, "test_chart.png")

    generate_comparison_chart(base_metrics, ft_metrics, chart_path)

    assert os.path.exists(chart_path)
    assert os.path.getsize(chart_path) > 0


def test_run_evaluation_e2e(eval_config_path: str, eval_output_dir: str) -> None:
    """End-to-end smoke test evaluating only the base model (no fine-tuned)."""
    report = run_evaluation(
        base_model_name=TINY_TEST_MODEL,
        finetuned_model_path=None,
        eval_config_path=eval_config_path,
        output_dir=eval_output_dir,
    )

    assert "base_metrics" in report
    assert "base_answers" in report
    assert "report_path" in report

    base_m = report["base_metrics"]
    assert "rouge1" in base_m
    assert "bleu" in base_m
    assert "bertscore_f1" in base_m

    assert os.path.exists(report["report_path"])
    with open(report["report_path"], encoding="utf-8") as f:
        saved = json.load(f)
    assert "base_metrics" in saved
