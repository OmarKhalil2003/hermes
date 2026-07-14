import json
import os
import shutil
from collections.abc import Generator

import pytest

from finetuning.merge import merge_adapters
from finetuning.preprocess import compile_dataset
from finetuning.train import train_model

# Use a tiny random model for testing to avoid heavy downloads and memory overhead
TINY_TEST_MODEL = "sshleifer/tiny-gpt2"


@pytest.fixture
def temp_dirs() -> Generator[dict[str, str]]:
    """Sets up and tears down temporary folders for training outputs."""
    dirs = {
        "dataset": "tests/temp_finetuning/dataset.jsonl",
        "adapters": "tests/temp_finetuning/adapters",
        "merged": "tests/temp_finetuning/merged",
    }
    os.makedirs(os.path.dirname(dirs["dataset"]), exist_ok=True)
    yield dirs
    # Clean up temp folders
    if os.path.exists("tests/temp_finetuning"):
        shutil.rmtree("tests/temp_finetuning")


@pytest.mark.asyncio
async def test_preprocess_pipeline(temp_dirs: dict[str, str]) -> None:
    """Verifies dataset compile preprocessor parses input format correctly."""
    output_path = temp_dirs["dataset"]

    # Run compiler
    await compile_dataset(output_path)

    # Assert dataset was created and contains valid JSON lines
    assert os.path.exists(output_path) is True

    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 0

        # Verify schema
        first_item = json.loads(lines[0])
        assert "messages" in first_item
        assert len(first_item["messages"]) >= 2
        assert first_item["messages"][0]["role"] == "user"
        assert first_item["messages"][1]["role"] == "assistant"


def test_train_and_merge_pipeline(temp_dirs: dict[str, str]) -> None:
    """Verifies QLoRA training and adapter merging loops execute without errors."""
    dataset_path = temp_dirs["dataset"]
    adapters_dir = temp_dirs["adapters"]
    merged_dir = temp_dirs["merged"]

    # 1. Compile test dataset
    import asyncio

    asyncio.run(compile_dataset(dataset_path))

    # 2. Run training loop for 1 step as a smoke test
    train_model(
        model_name=TINY_TEST_MODEL,
        dataset_path=dataset_path,
        output_dir=adapters_dir,
        epochs=1,
        batch_size=1,
        learning_rate=2e-4,
        lora_r=4,
        lora_alpha=8,
        max_steps=1,
    )

    # Verify adapters are saved to output directory
    assert os.path.exists(adapters_dir) is True
    assert os.path.exists(os.path.join(adapters_dir, "adapter_config.json")) is True

    # 3. Merge adapters back into base model
    merge_adapters(
        base_model_name=TINY_TEST_MODEL,
        adapter_path=adapters_dir,
        output_dir=merged_dir,
    )

    # Verify merged weights folder was created
    assert os.path.exists(merged_dir) is True
    assert os.path.exists(os.path.join(merged_dir, "config.json")) is True
