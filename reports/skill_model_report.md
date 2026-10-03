# Training Report: question-skill-tagger-v1

**Generated:** 2026-10-03T06:39:01.034274+00:00  
**Model Version:** 1.1.0  
**Task:** multilabel_classification  
**Base Architecture:** TF-IDF + OneVsRest(LogisticRegression)

## Reproducibility

| Parameter | Value |
| :--- | :--- |
| Random Seed | `42` |
| Dataset Hash | `e6b25c8cbaa4c28e` |
| Preprocessing Version | `1.0.0` |
| Artifact Hash | `ad21e4620e357e561f34b9fd173b28f53966985e7cf1246b84c9391df420e7a2` |
| Training Duration | `12.39s` |
| Python | `3.12.0` |
| Platform | `Windows-11-10.0.26200-SP0` |

## Dataset

| Property | Value |
| :--- | :--- |
| Identifier | BAAI/TACO |
| Version | 2026.10 |
| Train Samples | 1820 |
| Validation Samples | 260 |
| Test Samples | 520 |

## Hyperparameters

```json
{
  "vectorizer": {
    "max_features": 6000,
    "ngram_range": [
      1,
      2
    ],
    "stop_words": "english",
    "sublinear_tf": true
  },
  "classifier": {
    "C": 2.0,
    "max_iter": 1000,
    "class_weight": "balanced",
    "solver": "lbfgs"
  },
  "prediction_threshold": 0.3,
  "min_predictions_per_sample": 1
}
```

## Validation Metrics

| Metric | Value |
| :--- | :--- |
| micro_f1 | 0.6487 |
| macro_f1 | 0.6020 |
| precision.micro | 0.5067 |
| precision.macro | 0.5610 |
| recall.micro | 0.9014 |
| recall.macro | 0.7647 |
| hamming_loss | 0.0907 |
| per_class.arrays.precision | 0.6667 |
| per_class.arrays.recall | 0.8889 |
| per_class.arrays.f1 | 0.7619 |
| per_class.arrays.support | 9 |
| per_class.hashing.precision | 0.2727 |
| per_class.hashing.recall | 0.6000 |
| per_class.hashing.f1 | 0.3750 |
| per_class.hashing.support | 5 |
| per_class.strings.precision | 0.4634 |
| per_class.strings.recall | 0.8636 |
| per_class.strings.f1 | 0.6032 |
| per_class.strings.support | 22 |
| per_class.sorting.precision | 0.1974 |
| per_class.sorting.recall | 0.8824 |
| per_class.sorting.f1 | 0.3226 |
| per_class.sorting.support | 17 |
| per_class.search.precision | 0.1481 |
| per_class.search.recall | 0.6667 |
| per_class.search.f1 | 0.2424 |
| per_class.search.support | 18 |
| per_class.two_pointers.precision | 0.2000 |
| per_class.two_pointers.recall | 0.3333 |
| per_class.two_pointers.f1 | 0.2500 |
| per_class.two_pointers.support | 3 |
| per_class.sliding_window.precision | 0.0000 |
| per_class.sliding_window.recall | 0.0000 |
| per_class.sliding_window.f1 | 0.0000 |
| per_class.sliding_window.support | 0 |
| per_class.trees.precision | 0.3462 |
| per_class.trees.recall | 0.6923 |
| per_class.trees.f1 | 0.4615 |
| per_class.trees.support | 13 |
| per_class.graphs.precision | 0.3488 |
| per_class.graphs.recall | 0.7500 |
| per_class.graphs.f1 | 0.4762 |
| per_class.graphs.support | 20 |
| per_class.dynamic_programming.precision | 0.1910 |
| per_class.dynamic_programming.recall | 0.7727 |
| per_class.dynamic_programming.f1 | 0.3063 |
| per_class.dynamic_programming.support | 22 |
| per_class.greedy.precision | 0.2468 |
| per_class.greedy.recall | 0.8261 |
| per_class.greedy.f1 | 0.3800 |
| per_class.greedy.support | 23 |
| per_class.backtracking.precision | 1.00 |
| per_class.backtracking.recall | 0.6250 |
| per_class.backtracking.f1 | 0.7692 |
| per_class.backtracking.support | 8 |
| per_class.heaps.precision | 1.00 |
| per_class.heaps.recall | 0.5000 |
| per_class.heaps.f1 | 0.6667 |
| per_class.heaps.support | 2 |
| per_class.stacks.precision | 1.00 |
| per_class.stacks.recall | 1.00 |
| per_class.stacks.f1 | 1.00 |
| per_class.stacks.support | 2 |
| per_class.queues.precision | 1.00 |
| per_class.queues.recall | 1.00 |
| per_class.queues.f1 | 1.00 |
| per_class.queues.support | 4 |
| per_class.linked_lists.precision | 1.00 |
| per_class.linked_lists.recall | 1.00 |
| per_class.linked_lists.f1 | 1.00 |
| per_class.linked_lists.support | 4 |
| per_class.binary_search.precision | 1.00 |
| per_class.binary_search.recall | 1.00 |
| per_class.binary_search.f1 | 1.00 |
| per_class.binary_search.support | 2 |
| per_class.recursion.precision | 0.5000 |
| per_class.recursion.recall | 0.8571 |
| per_class.recursion.f1 | 0.6316 |
| per_class.recursion.support | 7 |
| per_class.complexity.precision | 0.9062 |
| per_class.complexity.recall | 1.00 |
| per_class.complexity.f1 | 0.9508 |
| per_class.complexity.support | 29 |
| per_class.data_structures.precision | 0.3254 |
| per_class.data_structures.recall | 0.8039 |
| per_class.data_structures.f1 | 0.4633 |
| per_class.data_structures.support | 51 |
| per_class.algorithms.precision | 0.9684 |
| per_class.algorithms.recall | 0.9959 |
| per_class.algorithms.f1 | 0.9820 |
| per_class.algorithms.support | 246 |

## Test Metrics

| Metric | Value |
| :--- | :--- |
| micro_f1 | 0.6453 |
| macro_f1 | 0.4994 |
| precision.micro | 0.5145 |
| precision.macro | 0.4513 |
| recall.micro | 0.8652 |
| recall.macro | 0.6573 |
| hamming_loss | 0.0962 |
| per_class.arrays.precision | 0.5625 |
| per_class.arrays.recall | 0.5625 |
| per_class.arrays.f1 | 0.5625 |
| per_class.arrays.support | 16 |
| per_class.hashing.precision | 0.2400 |
| per_class.hashing.recall | 0.7500 |
| per_class.hashing.f1 | 0.3636 |
| per_class.hashing.support | 8 |
| per_class.strings.precision | 0.5104 |
| per_class.strings.recall | 0.8909 |
| per_class.strings.f1 | 0.6490 |
| per_class.strings.support | 55 |
| per_class.sorting.precision | 0.2284 |
| per_class.sorting.recall | 0.6852 |
| per_class.sorting.f1 | 0.3426 |
| per_class.sorting.support | 54 |
| per_class.search.precision | 0.1279 |
| per_class.search.recall | 0.5500 |
| per_class.search.f1 | 0.2075 |
| per_class.search.support | 40 |
| per_class.two_pointers.precision | 0.6000 |
| per_class.two_pointers.recall | 0.6000 |
| per_class.two_pointers.f1 | 0.6000 |
| per_class.two_pointers.support | 5 |
| per_class.sliding_window.precision | 0.0000 |
| per_class.sliding_window.recall | 0.0000 |
| per_class.sliding_window.f1 | 0.0000 |
| per_class.sliding_window.support | 0 |
| per_class.trees.precision | 0.3830 |
| per_class.trees.recall | 0.6667 |
| per_class.trees.f1 | 0.4865 |
| per_class.trees.support | 27 |
| per_class.graphs.precision | 0.3294 |
| per_class.graphs.recall | 0.6512 |
| per_class.graphs.f1 | 0.4375 |
| per_class.graphs.support | 43 |
| per_class.dynamic_programming.precision | 0.2287 |
| per_class.dynamic_programming.recall | 0.8113 |
| per_class.dynamic_programming.f1 | 0.3568 |
| per_class.dynamic_programming.support | 53 |
| per_class.greedy.precision | 0.3026 |
| per_class.greedy.recall | 0.8214 |
| per_class.greedy.f1 | 0.4423 |
| per_class.greedy.support | 56 |
| per_class.backtracking.precision | 0.6923 |
| per_class.backtracking.recall | 1.00 |
| per_class.backtracking.f1 | 0.8182 |
| per_class.backtracking.support | 9 |
| per_class.heaps.precision | 0.0000 |
| per_class.heaps.recall | 0.0000 |
| per_class.heaps.f1 | 0.0000 |
| per_class.heaps.support | 0 |
| per_class.stacks.precision | 1.00 |
| per_class.stacks.recall | 0.5385 |
| per_class.stacks.f1 | 0.7000 |
| per_class.stacks.support | 13 |
| per_class.queues.precision | 0.7500 |
| per_class.queues.recall | 0.7500 |
| per_class.queues.f1 | 0.7500 |
| per_class.queues.support | 4 |
| per_class.linked_lists.precision | 0.3333 |
| per_class.linked_lists.recall | 1.00 |
| per_class.linked_lists.f1 | 0.5000 |
| per_class.linked_lists.support | 2 |
| per_class.binary_search.precision | 0.5000 |
| per_class.binary_search.recall | 0.5000 |
| per_class.binary_search.f1 | 0.5000 |
| per_class.binary_search.support | 4 |
| per_class.recursion.precision | 0.4000 |
| per_class.recursion.recall | 0.3333 |
| per_class.recursion.f1 | 0.3636 |
| per_class.recursion.support | 12 |
| per_class.complexity.precision | 0.9306 |
| per_class.complexity.recall | 0.8481 |
| per_class.complexity.f1 | 0.8874 |
| per_class.complexity.support | 79 |
| per_class.data_structures.precision | 0.4021 |
| per_class.data_structures.recall | 0.8519 |
| per_class.data_structures.f1 | 0.5463 |
| per_class.data_structures.support | 135 |
| per_class.algorithms.precision | 0.9567 |
| per_class.algorithms.recall | 0.9918 |
| per_class.algorithms.f1 | 0.9739 |
| per_class.algorithms.support | 490 |

## Per-Class Breakdown

| Class | Precision | Recall | F1 | Support |
| :--- | :--- | :--- | :--- | :--- |
| `arrays` | 0.5625 | 0.5625 | 0.5625 | 16 |
| `hashing` | 0.2400 | 0.7500 | 0.3636 | 8 |
| `strings` | 0.5104 | 0.8909 | 0.6490 | 55 |
| `sorting` | 0.2284 | 0.6852 | 0.3426 | 54 |
| `search` | 0.1279 | 0.5500 | 0.2075 | 40 |
| `two_pointers` | 0.6000 | 0.6000 | 0.6000 | 5 |
| `sliding_window` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `trees` | 0.3830 | 0.6667 | 0.4865 | 27 |
| `graphs` | 0.3294 | 0.6512 | 0.4375 | 43 |
| `dynamic_programming` | 0.2287 | 0.8113 | 0.3568 | 53 |
| `greedy` | 0.3026 | 0.8214 | 0.4423 | 56 |
| `backtracking` | 0.6923 | 1.00 | 0.8182 | 9 |
| `heaps` | 0.0000 | 0.0000 | 0.0000 | 0 |
| `stacks` | 1.00 | 0.5385 | 0.7000 | 13 |
| `queues` | 0.7500 | 0.7500 | 0.7500 | 4 |
| `linked_lists` | 0.3333 | 1.00 | 0.5000 | 2 |
| `binary_search` | 0.5000 | 0.5000 | 0.5000 | 4 |
| `recursion` | 0.4000 | 0.3333 | 0.3636 | 12 |
| `complexity` | 0.9306 | 0.8481 | 0.8874 | 79 |
| `data_structures` | 0.4021 | 0.8519 | 0.5463 | 135 |
| `algorithms` | 0.9567 | 0.9918 | 0.9739 | 490 |

## Label Coverage Summary

**Strong labels** (F1 ≥ 0.50): `arrays`, `strings`, `two_pointers`, `backtracking`, `stacks`, `queues`, `linked_lists`, `binary_search`, `complexity`, `data_structures`, `algorithms`

**Weak labels** (0 < F1 < 0.50): `hashing`, `sorting`, `search`, `trees`, `graphs`, `dynamic_programming`, `greedy`, `recursion`

**Zero-support labels** (F1 = 0.00): `sliding_window`, `heaps`
