from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from app.core.intent_labels import INTENT_LABELS
from app.utils.file_loader import resolve_path


def load_jsonl(path: str) -> list[dict[str, Any]]:
    file_path = resolve_path(path)
    rows: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def multi_hot(labels: list[str]) -> list[float]:
    label_set = set(labels)
    return [1.0 if label in label_set else 0.0 for label in INTENT_LABELS]


class IntentDataset:
    def __init__(self, rows: list[dict[str, Any]], tokenizer: Any, max_length: int = 160) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        import torch

        row = self.rows[idx]
        encoded = self.tokenizer(
            row["text"],
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"][0],
            "attention_mask": encoded["attention_mask"][0],
            "labels": torch.tensor(multi_hot(row["labels"]), dtype=torch.float32),
        }


def evaluate(model: Any, dataloader: Any, threshold: float = 0.5) -> dict[str, float]:
    import torch

    model.eval()
    tp = fp = fn = 0
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in INTENT_LABELS}
    with torch.no_grad():
        for batch in dataloader:
            labels = batch.pop("labels")
            outputs = model(**batch)
            preds = (torch.sigmoid(outputs.logits) >= threshold).int()
            gold = labels.int()
            tp += int(((preds == 1) & (gold == 1)).sum())
            fp += int(((preds == 1) & (gold == 0)).sum())
            fn += int(((preds == 0) & (gold == 1)).sum())
            for idx, label in enumerate(INTENT_LABELS):
                per_label[label]["tp"] += int(((preds[:, idx] == 1) & (gold[:, idx] == 1)).sum())
                per_label[label]["fp"] += int(((preds[:, idx] == 1) & (gold[:, idx] == 0)).sum())
                per_label[label]["fn"] += int(((preds[:, idx] == 0) & (gold[:, idx] == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    macro_f1_values = []
    for stats in per_label.values():
        p = stats["tp"] / max(stats["tp"] + stats["fp"], 1)
        r = stats["tp"] / max(stats["tp"] + stats["fn"], 1)
        macro_f1_values.append(2 * p * r / max(p + r, 1e-8))
    return {
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "macro_f1": round(sum(macro_f1_values) / max(len(macro_f1_values), 1), 4),
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    random.seed(args.seed)
    rows = load_jsonl(args.train_file)
    random.shuffle(rows)
    split = max(1, int(len(rows) * (1 - args.val_ratio)))
    train_rows = rows[:split]
    val_rows = rows[split:] or rows[: min(32, len(rows))]

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, local_files_only=args.local_files_only)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(INTENT_LABELS),
        problem_type="multi_label_classification",
        local_files_only=args.local_files_only,
    )
    train_loader = DataLoader(IntentDataset(train_rows, tokenizer, args.max_length), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(IntentDataset(val_rows, tokenizer, args.max_length), batch_size=args.batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model.to(device)

    def move_batch(batch: dict[str, Any]) -> dict[str, Any]:
        return {key: value.to(device) for key, value in batch.items()}

    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            batch = move_batch(batch)
            optimizer.zero_grad()
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu())
        model.to("cpu")
        metrics = evaluate(model, val_loader, threshold=args.threshold)
        model.to(device)
        metrics["epoch"] = epoch
        metrics["train_loss"] = round(total_loss / max(len(train_loader), 1), 4)
        history.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False))

    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.to("cpu")
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    (output_dir / "label_mapping.json").write_text(
        json.dumps({"labels": INTENT_LABELS, "threshold": args.threshold}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "training_metrics.json").write_text(
        json.dumps({"history": history, "train_size": len(train_rows), "val_size": len(val_rows)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"output_dir": str(output_dir), "train_size": len(train_rows), "val_size": len(val_rows), "last_metrics": history[-1]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune BERT-mini for AI coach multi-label intent classification.")
    parser.add_argument("--train-file", default="data/intent_training_samples.jsonl")
    parser.add_argument("--model-name", default="uer/chinese_roberta_L-2_H-128")
    parser.add_argument("--output-dir", default="models/bert_mini_intent")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=160)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()
    result = train(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

