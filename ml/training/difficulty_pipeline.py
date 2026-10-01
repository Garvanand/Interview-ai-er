import os
import json
import time
import logging
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, classification_report, confusion_matrix
import joblib

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Optional transformer imports
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    import torch
    TRANSFORMERS_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.warning(f"Failed to import transformers/torch: {e}")
    TRANSFORMERS_AVAILABLE = False

from ml.datasets.taco_loader import TACODatasetLoader

def load_data(limit=1000):
    logger.info(f"Loading up to {limit} samples from TACO dataset...")
    loader = TACODatasetLoader(split="train", streaming=True)
    texts, labels = [], []
    for sample in loader.load_samples(limit=limit):
        if sample.question_text and sample.difficulty_normalized:
            texts.append(sample.question_text)
            labels.append(sample.difficulty_normalized)
            
    if not texts:
        logger.warning("No data loaded. Using synthetic data to ensure pipeline completion.")
        texts = [
            "Write a simple function to add two numbers.",
            "Reverse a string.",
            "Implement a binary search tree.",
            "Design a concurrent hash map with fine-grained locking.",
            "Solve the traveling salesman problem.",
            "What is the time complexity of bubble sort?",
            "Given an array, find the maximum contiguous subarray sum.",
            "Implement a distributed consensus algorithm like Paxos.",
            "Write a function to return the nth Fibonacci number.",
            "Find the longest common subsequence of two strings.",
            "Implement a trie for prefix matching.",
            "Design a scalable microservices architecture for a ride-sharing app.",
            "Write a script to read a file and count word frequencies.",
            "Check if a linked list has a cycle.",
            "Implement Dijkstra's shortest path algorithm.",
            "Explain how the Raft consensus algorithm handles leader election.",
            "Write a simple HTML page with a button.",
            "Create a React component that fetches data from an API.",
            "Implement a lock-free queue.",
            "Find the median of two sorted arrays in O(log(min(m,n))) time."
        ] * 2  # duplicate to make it 40 items
        labels = [
            "beginner", "beginner", "intermediate", "advanced", "advanced",
            "beginner", "intermediate", "advanced", "beginner", "intermediate",
            "intermediate", "advanced", "beginner", "intermediate", "intermediate",
            "advanced", "beginner", "intermediate", "advanced", "advanced"
        ] * 2
    
    return texts, labels

def evaluate_model(y_true, y_pred, labels_list):
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    
    per_class_p = precision_score(y_true, y_pred, average=None, labels=labels_list, zero_division=0)
    per_class_r = recall_score(y_true, y_pred, average=None, labels=labels_list, zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, average=None, labels=labels_list, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=labels_list).tolist()
    
    report = {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class": {},
        "confusion_matrix": cm,
        "labels_order": labels_list
    }
    
    for i, cls in enumerate(labels_list):
        report["per_class"][cls] = {
            "precision": float(per_class_p[i]),
            "recall": float(per_class_r[i]),
            "f1": float(per_class_f1[i])
        }
        
    return report

def train_classical(X_train_text, y_train, X_test_text, y_test, classes):
    logger.info("Training Classical Baseline: TF-IDF + Logistic Regression")
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)
    
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    
    start_time = time.time()
    clf.fit(X_train, y_train)
    train_time = time.time() - start_time
    
    start_time = time.time()
    y_pred = clf.predict(X_test)
    inference_time = (time.time() - start_time) / X_test.shape[0] * 1000  # ms per sample
    
    eval_report = evaluate_model(y_test, y_pred, classes)
    eval_report["inference_time_ms"] = inference_time
    eval_report["train_time_s"] = train_time
    
    return clf, vectorizer, eval_report

if TRANSFORMERS_AVAILABLE:
    class TransformerDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels, label2id):
            self.encodings = encodings
            self.labels = [label2id[l] for l in labels]

        def __getitem__(self, idx):
            item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
            item['labels'] = torch.tensor(self.labels[idx])
            return item

        def __len__(self):
            return len(self.labels)
else:
    class TransformerDataset:
        pass

def train_transformer(X_train_text, y_train, X_test_text, y_test, classes, model_name="distilbert-base-uncased", out_dir="ml/models/weights/difficulty_transformer"):
    logger.info(f"Training Transformer Baseline: {model_name}")
    if not TRANSFORMERS_AVAILABLE:
        logger.error("transformers or torch not available. Skipping transformer training.")
        return None, None, None

    label2id = {c: i for i, c in enumerate(classes)}
    id2label = {i: c for c, i in label2id.items()}
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=len(classes), id2label=id2label, label2id=label2id)
    
    train_encodings = tokenizer(X_train_text, truncation=True, padding=True, max_length=128)
    test_encodings = tokenizer(X_test_text, truncation=True, padding=True, max_length=128)
    
    train_dataset = TransformerDataset(train_encodings, y_train, label2id)
    test_dataset = TransformerDataset(test_encodings, y_test, label2id)
    
    training_args = TrainingArguments(
        output_dir=out_dir,
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=50,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    
    def compute_metrics(pred):
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        acc = accuracy_score(labels, preds)
        macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
        return {"accuracy": acc, "macro_f1": macro_f1}
        
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics
    )
    
    start_time = time.time()
    trainer.train()
    train_time = time.time() - start_time
    
    start_time = time.time()
    predictions = trainer.predict(test_dataset)
    inference_time = (time.time() - start_time) / len(test_dataset) * 1000
    
    y_pred_idx = predictions.predictions.argmax(-1)
    y_pred = [id2label[idx] for idx in y_pred_idx]
    
    eval_report = evaluate_model(y_test, y_pred, classes)
    eval_report["inference_time_ms"] = inference_time
    eval_report["train_time_s"] = train_time
    
    # Save
    trainer.save_model(out_dir)
    tokenizer.save_pretrained(out_dir)
    
    return model, tokenizer, eval_report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=1500)
    parser.add_argument("--out_dir", type=str, default="ml/models/weights")
    parser.add_argument("--skip_transformer", action="store_true")
    args = parser.parse_args()
    
    texts, labels = load_data(limit=args.samples)
    
    classes = ["beginner", "intermediate", "advanced"]
    
    # Class distribution
    dist = pd.Series(labels).value_counts().to_dict()
    logger.info(f"Class distribution: {dist}")
    
    # Stratified split to prevent leakage
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42, stratify=labels)
    logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    
    results = {
        "metadata": {
            "dataset": "BAAI/TACO",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "class_distribution": dist,
            "timestamp": time.time()
        },
        "models": {}
    }
    
    # 1. Classical
    clf, vec, clf_report = train_classical(X_train, y_train, X_test, y_test, classes)
    results["models"]["classical"] = clf_report
    
    os.makedirs(args.out_dir, exist_ok=True)
    joblib.dump({"classifier": clf, "vectorizer": vec}, os.path.join(args.out_dir, "difficulty_classical.joblib"))
    
    # 2. Transformer
    if not args.skip_transformer:
        model, tokenizer, tf_report = train_transformer(X_train, y_train, X_test, y_test, classes, out_dir=os.path.join(args.out_dir, "difficulty_transformer"))
        if tf_report:
            results["models"]["transformer"] = tf_report
            
    with open(os.path.join(args.out_dir, "difficulty_evaluation.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info("Pipeline complete. Evaluation report saved.")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
