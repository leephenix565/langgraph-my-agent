#!/usr/bin/env python
"""Train Router-SFT with QLoRA using prepared messages JSONL."""

from __future__ import annotations

import argparse
import inspect
import json
import os
from typing import Any, Dict, List

import torch
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer


def _format_messages(tokenizer, messages: List[Dict[str, Any]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(role, str) and isinstance(content, str):
            parts.append(f"{role}: {content}")
    return "\n\n".join(parts)


def _filter_kwargs(fn, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    sig = inspect.signature(fn)
    params = set(sig.parameters)
    return {k: v for k, v in kwargs.items() if k in params}


def main() -> int:
    ap = argparse.ArgumentParser(description="QLoRA SFT training for Router-SFT.")
    ap.add_argument("--base-model-path", required=True)
    ap.add_argument("--train-jsonl", required=True)
    ap.add_argument("--val-jsonl", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--max-seq-len", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-device-train-batch-size", type=int, default=1)
    ap.add_argument("--gradient-accumulation-steps", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--num-epochs", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--logging-steps", type=int, default=10)
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--eval-steps", type=int, default=200)
    ap.add_argument("--max-train-samples", type=int, default=None)
    ap.add_argument("--max-eval-samples", type=int, default=None)
    ap.add_argument("--merge-and-save-full-model", action="store_true")
    args = ap.parse_args()

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(args.base_model_path, use_fast=True, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.model_max_length = args.max_seq_len

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    data_files = {"train": args.train_jsonl, "validation": args.val_jsonl}
    dataset = load_dataset("json", data_files=data_files)
    if args.max_train_samples is not None:
        dataset["train"] = dataset["train"].select(range(min(args.max_train_samples, len(dataset["train"]))))
    if args.max_eval_samples is not None:
        dataset["validation"] = dataset["validation"].select(range(min(args.max_eval_samples, len(dataset["validation"]))))

    def formatting_func(example: Dict[str, Any]) -> str:
        text = example.get("text")
        if isinstance(text, str) and text:
            return text
        messages = example.get("messages") or []
        return _format_messages(tokenizer, messages)

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    ta_kwargs: Dict[str, Any] = {
        "output_dir": args.output_dir,
        "num_train_epochs": args.num_epochs,
        "max_steps": args.max_steps if args.max_steps and args.max_steps > 0 else -1,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.lr,
        "logging_steps": args.logging_steps,
        "save_steps": args.save_steps,
        "eval_steps": args.eval_steps,
        "save_total_limit": 2,
        "bf16": bf16,
        "fp16": False,
        "report_to": [],
        "seed": args.seed,
    }
    if "eval_strategy" in inspect.signature(TrainingArguments.__init__).parameters:
        ta_kwargs["eval_strategy"] = "steps"
    else:
        ta_kwargs["evaluation_strategy"] = "steps"
    training_args = TrainingArguments(**_filter_kwargs(TrainingArguments.__init__, ta_kwargs))

    trainer_kwargs: Dict[str, Any] = {
        "model": model,
        "train_dataset": dataset["train"],
        "eval_dataset": dataset["validation"],
        "peft_config": peft_config,
        "formatting_func": formatting_func,
        "args": training_args,
    }
    sig = inspect.signature(SFTTrainer.__init__).parameters
    if "processing_class" in sig:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in sig:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = SFTTrainer(**_filter_kwargs(SFTTrainer.__init__, trainer_kwargs))

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    if args.merge_and_save_full_model:
        merged = trainer.model.merge_and_unload()
        merged_dir = os.path.join(args.output_dir, "merged")
        os.makedirs(merged_dir, exist_ok=True)
        merged.save_pretrained(merged_dir, safe_serialization=True)
        tokenizer.save_pretrained(merged_dir)

    print("train_done:")
    print("  output_dir:", args.output_dir)
    if args.merge_and_save_full_model:
        print("  merged_dir:", os.path.join(args.output_dir, "merged"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
