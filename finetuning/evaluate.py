"""Automated evaluation pipeline comparing base vs fine-tuned models.

Computes ROUGE, BLEU, BERTScore, and optionally RAGAS metrics, then logs
comparison results and charts to MLflow.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import mlflow
import nltk
import numpy as np
import torch
from rouge_score import rouge_scorer
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizerBase

matplotlib.use("Agg")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EvalSample:
    """A single evaluation sample with query, ground truth, and context."""

    query: str
    ground_truth: str
    context: str


def load_eval_config(path: str) -> list[EvalSample]:
    """Load and validate a JSON evaluation dataset.

    Args:
        path: Path to the JSON evaluation config file.

    Returns:
        Parsed list of EvalSample dataclasses.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If any sample is missing required keys.
    """
    with open(path, encoding="utf-8") as f:
        raw: list[dict[str, str]] = json.load(f)

    required_keys = {"query", "ground_truth", "context"}
    samples: list[EvalSample] = []
    for i, item in enumerate(raw):
        missing = required_keys - set(item.keys())
        if missing:
            msg = f"Sample {i} missing keys: {missing}"
            raise ValueError(msg)
        samples.append(
            EvalSample(
                query=item["query"],
                ground_truth=item["ground_truth"],
                context=item["context"],
            )
        )
    return samples


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def generate_answers(
    model: Any,
    tokenizer: PreTrainedTokenizerBase,
    samples: list[EvalSample],
    max_new_tokens: int = 128,
) -> list[str]:
    """Run inference on each evaluation query and return generated answers.

    Args:
        model: A HuggingFace causal language model.
        tokenizer: The tokenizer paired with *model*.
        samples: Evaluation samples containing the queries.
        max_new_tokens: Maximum tokens to generate per answer.

    Returns:
        List of generated answer strings (one per sample).
    """
    model.eval()
    device = next(model.parameters()).device
    answers: list[str] = []

    for sample in samples:
        prompt = (
            f"Context: {sample.context}\n\n" f"Question: {sample.query}\n\n" f"Answer:"
        )
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        input_ids = inputs["input_ids"].to(device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )

        # Decode only the newly generated tokens
        generated = outputs[0][input_ids.shape[1] :]
        decoded = tokenizer.decode(generated, skip_special_tokens=True)
        answer = decoded if isinstance(decoded, str) else decoded[0] if decoded else ""
        answer = answer.strip()
        answers.append(answer if answer else "(empty)")

    return answers


# ---------------------------------------------------------------------------
# Text metrics: ROUGE, BLEU, BERTScore
# ---------------------------------------------------------------------------


def compute_text_metrics(
    predictions: list[str],
    references: list[str],
) -> dict[str, float]:
    """Compute ROUGE, BLEU, and BERTScore metrics.

    Args:
        predictions: Model-generated answers.
        references: Ground-truth reference answers.

    Returns:
        Dictionary mapping metric names to float scores.
    """
    results: dict[str, float] = {}

    # --- ROUGE ---
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge_totals: dict[str, float] = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    for pred, ref in zip(predictions, references, strict=True):
        scores = scorer.score(ref, pred)
        for key in rouge_totals:
            rouge_totals[key] += scores[key].fmeasure
    n = max(len(predictions), 1)
    for key in rouge_totals:
        results[key] = rouge_totals[key] / n

    # --- BLEU ---
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)

    refs_tokenized = [nltk.word_tokenize(r.lower()) for r in references]
    preds_tokenized = [nltk.word_tokenize(p.lower()) for p in predictions]
    bleu = nltk.translate.bleu_score.corpus_bleu(
        [[r] for r in refs_tokenized],
        preds_tokenized,
    )
    results["bleu"] = float(bleu)

    # --- BERTScore ---
    try:
        from bert_score import score as bert_score_fn

        p, r, f1 = bert_score_fn(
            predictions,
            references,
            lang="en",
            verbose=False,
            rescale_with_baseline=False,
        )
        results["bertscore_precision"] = float(p.mean())
        results["bertscore_recall"] = float(r.mean())
        results["bertscore_f1"] = float(f1.mean())
    except Exception as exc:
        logger.warning("BERTScore computation failed: %s", exc)
        results["bertscore_precision"] = 0.0
        results["bertscore_recall"] = 0.0
        results["bertscore_f1"] = 0.0

    return results


# ---------------------------------------------------------------------------
# RAGAS metrics (optional — requires LLM API key)
# ---------------------------------------------------------------------------


def compute_ragas_metrics(
    queries: list[str],
    answers: list[str],
    contexts: list[str],
    ground_truths: list[str],
) -> dict[str, float]:
    """Compute RAGAS evaluation metrics if the library and API key are available.

    Metrics computed:
        - Faithfulness: Is the answer grounded in the context?
        - Answer Relevance: Does the answer address the query?
        - Context Recall: Does the context contain the ground truth?

    Args:
        queries: User questions.
        answers: Model-generated answers.
        contexts: Retrieved context passages.
        ground_truths: Reference ground-truth answers.

    Returns:
        Dictionary of RAGAS metric names to float scores, or empty dict
        if RAGAS is unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning(
            "OPENAI_API_KEY not set — skipping RAGAS metrics. "
            "Set the key to enable Faithfulness, Answer Relevance, "
            "and Context Recall evaluation."
        )
        return {}

    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_recall,
            faithfulness,
        )

        eval_dataset = Dataset.from_dict(
            {
                "question": queries,
                "answer": answers,
                "contexts": [[c] for c in contexts],
                "ground_truth": ground_truths,
            }
        )

        ragas_result = ragas_evaluate(
            dataset=eval_dataset,
            metrics=[faithfulness, answer_relevancy, context_recall],
        )

        return {
            "ragas_faithfulness": float(ragas_result["faithfulness"]),
            "ragas_answer_relevancy": float(ragas_result["answer_relevancy"]),
            "ragas_context_recall": float(ragas_result["context_recall"]),
        }
    except Exception as exc:
        logger.warning("RAGAS evaluation failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------


def generate_comparison_chart(
    base_metrics: dict[str, float],
    finetuned_metrics: dict[str, float],
    output_path: str,
) -> None:
    """Generate a grouped bar chart comparing base vs fine-tuned metrics.

    Args:
        base_metrics: Metric scores for the base model.
        finetuned_metrics: Metric scores for the fine-tuned model.
        output_path: File path to save the chart PNG.
    """
    # Only compare metrics present in both
    common_keys = sorted(set(base_metrics.keys()) & set(finetuned_metrics.keys()))
    if not common_keys:
        logger.warning("No common metrics to chart.")
        return

    x = np.arange(len(common_keys))
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(10, len(common_keys) * 1.5), 6))
    base_vals = [base_metrics[k] for k in common_keys]
    ft_vals = [finetuned_metrics[k] for k in common_keys]

    bars1 = ax.bar(x - width / 2, base_vals, width, label="Base Model", color="#4A90D9")
    bars2 = ax.bar(
        x + width / 2, ft_vals, width, label="Fine-Tuned Model", color="#E8724A"
    )

    ax.set_ylabel("Score")
    ax.set_title("Base vs Fine-Tuned Model Evaluation")
    ax.set_xticks(x)
    ax.set_xticklabels(common_keys, rotation=30, ha="right")
    ax.legend()
    ax.set_ylim(0, 1.05)

    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(
            f"{height:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(
            f"{height:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Full evaluation pipeline
# ---------------------------------------------------------------------------


def run_evaluation(
    base_model_name: str,
    finetuned_model_path: str | None,
    eval_config_path: str,
    output_dir: str,
) -> dict[str, Any]:
    """Run the complete evaluation comparing base vs fine-tuned models.

    Args:
        base_model_name: HuggingFace model name or local path for the base model.
        finetuned_model_path: Path to merged fine-tuned model weights, or None
            to evaluate only the base model.
        eval_config_path: Path to the JSON evaluation config file.
        output_dir: Directory for saving charts and JSON reports.

    Returns:
        Dictionary with ``base_metrics``, ``finetuned_metrics`` (if applicable),
        and file paths to generated artifacts.
    """
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("hermes-model-evaluation")

    # Load evaluation samples
    samples = load_eval_config(eval_config_path)
    queries = [s.query for s in samples]
    ground_truths = [s.ground_truth for s in samples]
    contexts = [s.context for s in samples]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_kwargs: dict[str, Any] = {}
    if device == "cpu":
        model_kwargs["torch_dtype"] = torch.float32
    model_kwargs["device_map"] = {"": device}

    os.makedirs(output_dir, exist_ok=True)
    report: dict[str, Any] = {}

    with mlflow.start_run(run_name="model-evaluation"):
        # ----- Base model evaluation -----
        logger.info("Loading base model: %s", base_model_name)
        base_tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        if base_tokenizer.pad_token is None:
            base_tokenizer.pad_token = base_tokenizer.eos_token

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name, **model_kwargs
        )

        base_answers = generate_answers(base_model, base_tokenizer, samples)
        base_text_metrics = compute_text_metrics(base_answers, ground_truths)
        base_ragas_metrics = compute_ragas_metrics(
            queries, base_answers, contexts, ground_truths
        )
        base_all_metrics = {**base_text_metrics, **base_ragas_metrics}

        mlflow.log_metrics({f"base_{k}": v for k, v in base_all_metrics.items()})
        report["base_metrics"] = base_all_metrics
        report["base_answers"] = base_answers

        # Free memory
        del base_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ----- Fine-tuned model evaluation (if provided) -----
        ft_all_metrics: dict[str, float] = {}
        if finetuned_model_path and os.path.isdir(finetuned_model_path):
            logger.info("Loading fine-tuned model: %s", finetuned_model_path)
            ft_tokenizer = AutoTokenizer.from_pretrained(finetuned_model_path)
            if ft_tokenizer.pad_token is None:
                ft_tokenizer.pad_token = ft_tokenizer.eos_token

            ft_model = AutoModelForCausalLM.from_pretrained(
                finetuned_model_path, **model_kwargs
            )

            ft_answers = generate_answers(ft_model, ft_tokenizer, samples)
            ft_text_metrics = compute_text_metrics(ft_answers, ground_truths)
            ft_ragas_metrics = compute_ragas_metrics(
                queries, ft_answers, contexts, ground_truths
            )
            ft_all_metrics = {**ft_text_metrics, **ft_ragas_metrics}

            mlflow.log_metrics({f"finetuned_{k}": v for k, v in ft_all_metrics.items()})
            report["finetuned_metrics"] = ft_all_metrics
            report["finetuned_answers"] = ft_answers

            del ft_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Generate comparison chart
            chart_path = os.path.join(output_dir, "comparison_chart.png")
            generate_comparison_chart(base_all_metrics, ft_all_metrics, chart_path)
            mlflow.log_artifact(chart_path)
            report["chart_path"] = chart_path

        # Save JSON report
        report_path = os.path.join(output_dir, "evaluation_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        mlflow.log_artifact(report_path)
        report["report_path"] = report_path

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate base vs fine-tuned model performance."
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Base model name or path.",
    )
    parser.add_argument(
        "--finetuned_model",
        type=str,
        default=None,
        help="Path to fine-tuned (merged) model directory.",
    )
    parser.add_argument(
        "--eval_config",
        type=str,
        default="finetuning/eval_config.json",
        help="Path to the evaluation JSON config.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="finetuning/eval_results",
        help="Directory for output charts and reports.",
    )

    args = parser.parse_args()
    run_evaluation(
        base_model_name=args.base_model,
        finetuned_model_path=args.finetuned_model,
        eval_config_path=args.eval_config,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
