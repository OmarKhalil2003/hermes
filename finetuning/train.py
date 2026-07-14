import argparse
import os

import mlflow
import mlflow.pytorch
import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer  # type: ignore[attr-defined]


def train_model(
    model_name: str,
    dataset_path: str,
    output_dir: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    lora_r: int,
    lora_alpha: int,
    max_steps: int = -1,
) -> None:
    """Configures 4-bit QLoRA and trains the instruction model,
    logging metrics to MLflow.
    """

    # 1. Setup MLflow Tracking Server or local repository
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("hermes-qlora-finetuning")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # 2. Configure 4-bit Quantization Config (if CUDA/GPU active)
    bnb_config = None
    if device == "cuda":
        from transformers import BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(  # type: ignore[no-untyped-call]
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=(
                torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            ),
        )

    # 3. Load Base Model and Tokenizer
    from typing import Any

    model_kwargs: dict[str, Any] = {}
    if bnb_config is not None:
        model_kwargs["quantization_config"] = bnb_config
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["device_map"] = {"": "cpu"}
        if device == "cpu":
            # Prevent float16 precision warnings on CPU
            model_kwargs["torch_dtype"] = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    # 4. Identify LoRA target modules dynamically to support diverse
    # test/base architectures
    model_modules = str(model.modules())
    target_modules = []
    for candidate in [
        "q_proj",
        "v_proj",
        "k_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
        "c_attn",
    ]:
        if candidate in model_modules:
            target_modules.append(candidate)

    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=target_modules if target_modules else None,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # 5. Format dataset with ChatML fallback
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    def format_chatml(messages: list[dict[str, str]]) -> str:
        try:
            return str(tokenizer.apply_chat_template(messages, tokenize=False))
        except Exception:
            text = ""
            for m in messages:
                text += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
            return text

    def process_data(batch: dict[str, Any]) -> dict[str, Any]:
        texts = []
        for messages in batch["messages"]:
            texts.append(format_chatml(messages))
        return {"text": texts}

    dataset = dataset.map(process_data, batched=True)
    dataset = dataset.remove_columns([c for c in dataset.column_names if c != "text"])

    # 6. Configure TRL SFTConfig parameters
    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_steps=1,
        save_strategy="no",
        report_to=["mlflow"],
        max_steps=max_steps,
        use_cpu=(device == "cpu"),
        dataset_text_field="text",
        max_length=512,
    )

    # 7. SFTTrainer Run wrapped in MLflow context
    with mlflow.start_run():
        mlflow.log_params(
            {
                "model_name": model_name,
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "lora_r": lora_r,
                "lora_alpha": lora_alpha,
                "target_modules": ",".join(target_modules),
            }
        )

        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            peft_config=peft_config,
            processing_class=tokenizer,
            args=training_args,
        )

        trainer.train()

        # Save trained adapter checkpoints to disk
        os.makedirs(output_dir, exist_ok=True)
        if trainer.model is not None:
            unwrapped = trainer.accelerator.unwrap_model(trainer.model)
            unwrapped.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        # Log adapters to MLflow Model Registry by loading clean model from disk
        if trainer.model is not None:
            from peft import PeftModel

            clean_base = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            clean_peft = PeftModel.from_pretrained(clean_base, output_dir)

            mlflow.pytorch.log_model(
                pytorch_model=clean_peft,
                artifact_path="adapters",
                registered_model_name="Hermes-QLoRA-Adapters",
                serialization_format="pickle",
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QLoRA Instruction Fine-tuning on Qwen."
    )
    parser.add_argument("--model_name", type=str, default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--dataset_path", type=str, default="finetuning/dataset.jsonl")
    parser.add_argument("--output_dir", type=str, default="finetuning/adapters")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=8)
    parser.add_argument("--lora_alpha", type=int, default=16)
    parser.add_argument("--max_steps", type=int, default=-1)

    args = parser.parse_args()

    train_model(
        model_name=args.model_name,
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        max_steps=args.max_steps,
    )


if __name__ == "__main__":
    main()
