#!/usr/bin/env python3
"""
Skeleton training script for IntentClassifier.

Phase 1: loads data, instantiates classifier, calls train() and save() (all no-ops).
Phase 2: replace IntentClassifier.train() stub with a real sklearn pipeline.

Usage:
    cd backend
    python3 -m classifier.train
"""

import json
from pathlib import Path

from classifier.intent_classifier import IntentClassifier

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "training_data.json"


def main():
    print(f"Loading training data from {DATA_PATH}")
    with open(DATA_PATH) as f:
        training_data = json.load(f)

    print(f"Loaded {len(training_data)} examples")

    clf = IntentClassifier()
    clf.train(training_data)
    clf.save()

    print("Training complete. Model saved.")


if __name__ == "__main__":
    main()
