# Training Report: question-difficulty-v1

**Generated:** 2026-10-03T06:38:25.325604+00:00  
**Model Version:** 1.1.0  
**Task:** multiclass_classification  
**Base Architecture:** TF-IDF + LogisticRegression

## Reproducibility

| Parameter | Value |
| :--- | :--- |
| Random Seed | `42` |
| Dataset Hash | `8c5f4fc319f43345` |
| Preprocessing Version | `1.0.0` |
| Artifact Hash | `12ef38983aa092caf9c187a70ef40c17ca197f93f4a439e1556d905dfcbf9843` |
| Training Duration | `18.32s` |
| Python | `3.12.0` |
| Platform | `Windows-11-10.0.26200-SP0` |

## Dataset

| Property | Value |
| :--- | :--- |
| Identifier | BAAI/TACO + codeparrot/apps |
| Version | 2026.10 |
| Train Samples | 1050 |
| Validation Samples | 150 |
| Test Samples | 300 |

## Hyperparameters

```json
{
  "classical": {
    "vectorizer": {
      "max_features": 5000,
      "ngram_range": [
        1,
        2
      ],
      "stop_words": "english",
      "sublinear_tf": true
    },
    "classifier": {
      "C": 1.0,
      "max_iter": 1000,
      "class_weight": "balanced",
      "solver": "lbfgs",
      "multi_class": "multinomial"
    }
  },
  "embedding": {
    "classifier": {
      "C": 2.0,
      "max_iter": 1000,
      "class_weight": "balanced",
      "solver": "lbfgs",
      "multi_class": "multinomial"
    }
  }
}
```

## Validation Metrics

| Metric | Value |
| :--- | :--- |
| accuracy | 0.5533 |
| macro_f1 | 0.5465 |
| weighted_f1 | 0.5422 |
| macro_precision | 0.5489 |
| macro_recall | 0.5612 |
| per_class.beginner.precision | 0.5385 |
| per_class.beginner.recall | 0.3962 |
| per_class.beginner.f1 | 0.4565 |
| per_class.beginner.support | 53 |
| per_class.intermediate.precision | 0.5208 |
| per_class.intermediate.recall | 0.5000 |
| per_class.intermediate.f1 | 0.5102 |
| per_class.intermediate.support | 50 |
| per_class.advanced.precision | 0.5873 |
| per_class.advanced.recall | 0.7872 |
| per_class.advanced.f1 | 0.6727 |
| per_class.advanced.support | 47 |

## Test Metrics

| Metric | Value |
| :--- | :--- |
| accuracy | 0.6567 |
| macro_f1 | 0.6558 |
| weighted_f1 | 0.6555 |
| macro_precision | 0.6664 |
| macro_recall | 0.6598 |
| per_class.beginner.precision | 0.7294 |
| per_class.beginner.recall | 0.5905 |
| per_class.beginner.f1 | 0.6526 |
| per_class.beginner.support | 105 |
| per_class.intermediate.precision | 0.6778 |
| per_class.intermediate.recall | 0.6100 |
| per_class.intermediate.f1 | 0.6421 |
| per_class.intermediate.support | 100 |
| per_class.advanced.precision | 0.5920 |
| per_class.advanced.recall | 0.7789 |
| per_class.advanced.f1 | 0.6727 |
| per_class.advanced.support | 95 |

## Per-Class Breakdown

| Class | Precision | Recall | F1 | Support |
| :--- | :--- | :--- | :--- | :--- |
| `beginner` | 0.7294 | 0.5905 | 0.6526 | 105 |
| `intermediate` | 0.6778 | 0.6100 | 0.6421 | 100 |
| `advanced` | 0.5920 | 0.7789 | 0.6727 | 95 |

## Confusion Matrix

| | `beginner` | `intermediate` | `advanced` |
| :--- | :---: | :---: | :---: |
| **`beginner`** | 62 | 17 | 26 |
| **`intermediate`** | 14 | 61 | 25 |
| **`advanced`** | 9 | 12 | 74 |
