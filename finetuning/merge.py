import argparse
import os

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge_adapters(base_model_name: str, adapter_path: str, output_dir: str) -> None:
    """Loads a base model and its PEFT adapters, merges them, and saves the
    final unified model weights.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    from typing import Any

    model_kwargs: dict[str, Any] = {}
    if device == "cuda":
        model_kwargs["torch_dtype"] = (
            torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        )
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = torch.float32
        model_kwargs["device_map"] = {"": "cpu"}

    base_model = AutoModelForCausalLM.from_pretrained(base_model_name, **model_kwargs)

    # Wrap base model with trained adapters
    model = PeftModel.from_pretrained(base_model, adapter_path)

    # Merge model weights and unload adapter wrapper
    merged_model = model.merge_and_unload()

    # Persist merged model and tokenizer to disk
    os.makedirs(output_dir, exist_ok=True)
    merged_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge PEFT adapters back into base model."
    )
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter_path", type=str, default="finetuning/adapters")
    parser.add_argument("--output_dir", type=str, default="finetuning/merged_model")

    args = parser.parse_args()

    merge_adapters(
        base_model_name=args.base_model,
        adapter_path=args.adapter_path,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
