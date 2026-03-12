#!/usr/bin/env python
"""Train a01 contract SFT with QLoRA using completion-only masking."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

torch = None
load_dataset = None
LoraConfig = None
get_peft_model = None
prepare_model_for_kbit_training = None
AutoModelForCausalLM = None
AutoTokenizer = None
BitsAndBytesConfig = None
Trainer = None
TrainingArguments = None
set_seed = None


def _load_training_deps() -> None:
    global torch
    global load_dataset
    global LoraConfig, get_peft_model, prepare_model_for_kbit_training
    global AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments, set_seed
    if torch is not None:
        return
    try:
        import torch as _torch
        from datasets import load_dataset as _load_dataset
        from peft import LoraConfig as _LoraConfig
        from peft import get_peft_model as _get_peft_model
        from peft import prepare_model_for_kbit_training as _prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM as _AutoModelForCausalLM,
            AutoTokenizer as _AutoTokenizer,
            BitsAndBytesConfig as _BitsAndBytesConfig,
            Trainer as _Trainer,
            TrainingArguments as _TrainingArguments,
            set_seed as _set_seed,
        )
    except Exception as exc:  # pragma: no cover - import guard for training envs
        raise SystemExit(f"Missing training deps. Install requirements-train.txt + requirements-hf.txt. ({exc})")

    torch = _torch
    load_dataset = _load_dataset
    LoraConfig = _LoraConfig
    get_peft_model = _get_peft_model
    prepare_model_for_kbit_training = _prepare_model_for_kbit_training
    AutoModelForCausalLM = _AutoModelForCausalLM
    AutoTokenizer = _AutoTokenizer
    BitsAndBytesConfig = _BitsAndBytesConfig
    Trainer = _Trainer
    TrainingArguments = _TrainingArguments
    set_seed = _set_seed


def _format_messages(tokenizer, messages: List[Dict[str, Any]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _filter_kwargs(fn, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    sig = inspect.signature(fn)
    params = set(sig.parameters)
    return {k: v for k, v in kwargs.items() if k in params}


def _find_lora_targets(model) -> List[str]:
    candidates = {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
    found: set[str] = set()
    for name, _module in model.named_modules():
        leaf = name.split(".")[-1]
        if leaf in candidates:
            found.add(leaf)
    return sorted(found) if found else sorted(candidates)


def _split_prompt_completion(tokenizer, messages: List[Dict[str, Any]], response_text: str) -> tuple[str, str]:
    prompt_msgs: List[Dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "assistant":
            continue
        prompt_msgs.append(msg)
    if hasattr(tokenizer, "apply_chat_template"):
        prompt_text = tokenizer.apply_chat_template(
            prompt_msgs, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt_text = _format_messages(tokenizer, prompt_msgs)
    completion_text = response_text
    return prompt_text, completion_text


def _tokenize_completion_only(
    tokenizer,
    prompt_text: str,
    completion_text: str,
    max_len: int,
) -> Dict[str, Any]:
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    completion_ids = tokenizer.encode(completion_text, add_special_tokens=False)
    eos_id = tokenizer.eos_token_id or tokenizer.sep_token_id or tokenizer.pad_token_id or 0
    if len(prompt_ids) + len(completion_ids) + 1 > max_len:
        avail = max_len - len(completion_ids) - 1
        if avail < 0:
            completion_ids = completion_ids[: max(0, max_len - 1)]
            prompt_ids = []
        else:
            prompt_ids = prompt_ids[-avail:]
    input_ids = prompt_ids + completion_ids + ([eos_id] if eos_id is not None else [])
    labels = [-100] * len(prompt_ids) + completion_ids + ([eos_id] if eos_id is not None else [])
    return {"input_ids": input_ids, "labels": labels}


class CompletionOnlyCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        max_len = max(len(f["input_ids"]) for f in features)
        pad_id = self.tokenizer.pad_token_id or 0
        input_ids = []
        attention_mask = []
        labels = []
        for f in features:
            ids = f["input_ids"]
            labs = f["labels"]
            pad_len = max_len - len(ids)
            input_ids.append(ids + [pad_id] * pad_len)
            attention_mask.append([1] * len(ids) + [0] * pad_len)
            labels.append(labs + [-100] * pad_len)
        return {
            "input_ids": torch.tensor(input_ids),
            "attention_mask": torch.tensor(attention_mask),
            "labels": torch.tensor(labels),
        }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _pkg_version(name: str) -> str:
    try:
        from importlib import metadata

        return metadata.version(name)
    except Exception:
        return "not_installed"


def _write_manifest(out_dir: Path, args: argparse.Namespace) -> None:
    manifest = {
        "git_commit": _git_commit(),
        "seed": args.seed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_paths": {
            "train_jsonl": args.train_jsonl,
            "val_jsonl": args.val_jsonl,
        },
        "data_sha256": {
            "train_jsonl": _sha256(Path(args.train_jsonl)),
            "val_jsonl": _sha256(Path(args.val_jsonl)),
        },
        "base_model_path": args.base_model_path,
        "output_dir": str(out_dir),
        "train_status": "completed",
        "python_version": sys.version,
        "package_versions": {
            "torch": _pkg_version("torch"),
            "transformers": _pkg_version("transformers"),
            "trl": _pkg_version("trl"),
            "peft": _pkg_version("peft"),
            "bitsandbytes": _pkg_version("bitsandbytes"),
            "datasets": _pkg_version("datasets"),
        },
        "train_args": {
            "max_seq_len": args.max_seq_len,
            "max_steps": args.max_steps,
            "max_train_samples": args.max_train_samples,
            "max_eval_samples": args.max_eval_samples,
            "lr": args.lr,
            "per_device_train_batch_size": args.per_device_train_batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
        },
    }
    out_path = out_dir / "run_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="QLoRA SFT training for a01 contract data.")
    ap.add_argument("--base-model-path", required=True)
    ap.add_argument("--train-jsonl", required=True)
    ap.add_argument("--val-jsonl", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--max-seq-len", type=int, default=8192)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-device-train-batch-size", type=int, default=1)
    ap.add_argument("--per-device-eval-batch-size", type=int, default=None)
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

    _load_training_deps()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)

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
        target_modules=_find_lora_targets(model),
    )
    model = get_peft_model(model, peft_config)
    if hasattr(model, "print_trainable_parameters"):
        model.print_trainable_parameters()

    data_files = {"train": args.train_jsonl, "validation": args.val_jsonl}
    dataset = load_dataset("json", data_files=data_files)
    if args.max_train_samples is not None:
        dataset["train"] = dataset["train"].select(range(min(args.max_train_samples, len(dataset["train"]))))
    if args.max_eval_samples is not None:
        dataset["validation"] = dataset["validation"].select(
            range(min(args.max_eval_samples, len(dataset["validation"])))
        )

    max_len = args.max_seq_len

    def tokenize_fn(example: Dict[str, Any]) -> Dict[str, Any]:
        messages = example.get("messages") or []
        response = example.get("response") or ""
        prompt_text, completion_text = _split_prompt_completion(tokenizer, messages, response)
        return _tokenize_completion_only(tokenizer, prompt_text, completion_text, max_len)

    column_names = dataset["train"].column_names
    tokenized_train = dataset["train"].map(tokenize_fn, remove_columns=column_names)
    tokenized_eval = dataset["validation"].map(tokenize_fn, remove_columns=column_names)

    data_collator = CompletionOnlyCollator(tokenizer)

    per_eval = (
        args.per_device_eval_batch_size
        if args.per_device_eval_batch_size is not None
        else args.per_device_train_batch_size
    )
    ta_kwargs: Dict[str, Any] = {
        "output_dir": str(out_dir),
        "num_train_epochs": args.num_epochs,
        "max_steps": args.max_steps if args.max_steps and args.max_steps > 0 else -1,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "per_device_eval_batch_size": per_eval,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.lr,
        "logging_steps": args.logging_steps,
        "save_steps": args.save_steps,
        "eval_steps": args.eval_steps,
        "eval_accumulation_steps": 1,
        "save_total_limit": 2,
        "bf16": torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
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
        "args": training_args,
        "train_dataset": tokenized_train,
        "eval_dataset": tokenized_eval,
        "data_collator": data_collator,
        "tokenizer": tokenizer,
    }
    trainer = Trainer(**_filter_kwargs(Trainer.__init__, trainer_kwargs))

    trainer.train()
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    if args.merge_and_save_full_model:
        merged = trainer.model.merge_and_unload()
        merged_dir = out_dir / "merged"
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged.save_pretrained(str(merged_dir), safe_serialization=True)
        tokenizer.save_pretrained(str(merged_dir))

    _write_manifest(out_dir, args)
    print("train_done:")
    print("  output_dir:", out_dir)
    if args.merge_and_save_full_model:
        print("  merged_dir:", out_dir / "merged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
