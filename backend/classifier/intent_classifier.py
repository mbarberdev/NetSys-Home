import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"


class IntentClassifier:
    """
    TfidfVectorizer + RandomForestClassifier pipeline for intent classification.

    Training data format: [{"text": "...", "label": "block|isolate|guest_network|schedule_block"}, ...]

    Phase 3 note: the public interface (train/predict/save/load) is stable.
    If intent extraction needs to handle OpenWRT-specific device names or MAC
    addresses in free text, extend the TfidfVectorizer's analyzer or add a
    preprocessing step before fitting — do not change the method signatures.
    """

    def __init__(self):
        self.pipeline: Pipeline | None = None
        self.is_trained: bool = False

    def train(self, training_data: list[dict]) -> None:
        X = [entry["text"] for entry in training_data]
        y = [entry["label"] for entry in training_data]

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
            )),
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=None,
                class_weight="balanced",
                random_state=42,
            )),
        ])
        self.pipeline.fit(X, y)
        self.is_trained = True

    def predict(self, text: str) -> dict:
        if not self.is_trained or self.pipeline is None:
            return {
                "predicted_action": "block",
                "confidence": None,
                "model": "stub",
            }

        proba = self.pipeline.predict_proba([text])[0]
        idx = int(np.argmax(proba))
        label = self.pipeline.classes_[idx]
        confidence = round(float(proba[idx]), 3)

        return {
            "predicted_action": label,
            "confidence": confidence,
            "model": "random_forest",
        }

    def save(self, path: Path | None = None) -> None:
        if self.pipeline is None:
            return
        joblib.dump(self.pipeline, path or MODEL_PATH)

    def load(self, path: Path | None = None) -> None:
        target = path or MODEL_PATH
        if not Path(target).exists():
            return
        self.pipeline = joblib.load(target)
        self.is_trained = True
