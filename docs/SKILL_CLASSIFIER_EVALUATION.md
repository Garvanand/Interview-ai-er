# TACO Multi-Label Question-Skill Classifier Evaluation Report

**Generated:** 2026-09-30T16:46:38.996939+00:00
**Dataset:** BAAI/TACO (Problem statements, tags, skill_types)
**Total Samples:** 2724 (Train: 2179, Test: 545)

## 1. Executive Summary

| Metric | TF-IDF + One-vs-Rest (Production) | Lightweight Transformer |
| :--- | :--- | :--- |
| **Micro F1** | **0.6763** | 0.3929 |
| **Macro F1** | **0.6712** | 0.2697 |
| **Micro Precision** | 0.5467 | 0.2504 |
| **Macro Precision** | 0.6217 | 0.1936 |
| **Micro Recall** | 0.8867 | 0.9116 |
| **Macro Recall** | 0.8124 | 0.677 |
| **Hamming Loss** | **0.0896** | 0.2933 |

## 2. Per-Label Breakdown (Canonical Taxonomy)

| Canonical Skill | Precision | Recall | F1 Score | Test Support |
| :--- | :--- | :--- | :--- | :--- |
| `arrays` | 0.7059 | 0.7500 | 0.7273 | 32 |
| `hashing` | 0.5714 | 0.8000 | 0.6667 | 15 |
| `strings` | 0.4800 | 0.8889 | 0.6234 | 54 |
| `sorting` | 0.2209 | 0.7755 | 0.3439 | 49 |
| `search` | 0.1647 | 0.7000 | 0.2667 | 40 |
| `two_pointers` | 0.8000 | 0.7273 | 0.7619 | 11 |
| `sliding_window` | 1.0000 | 1.0000 | 1.0000 | 4 |
| `trees` | 0.4068 | 0.8000 | 0.5393 | 30 |
| `graphs` | 0.3711 | 0.7660 | 0.5000 | 47 |
| `dynamic_programming` | 0.2787 | 0.8361 | 0.4180 | 61 |
| `greedy` | 0.3241 | 0.7966 | 0.4608 | 59 |
| `backtracking` | 0.6923 | 0.6429 | 0.6667 | 14 |
| `heaps` | 1.0000 | 0.7143 | 0.8333 | 7 |
| `stacks` | 1.0000 | 0.7273 | 0.8421 | 11 |
| `queues` | 0.8182 | 1.0000 | 0.9000 | 9 |
| `linked_lists` | 0.6667 | 1.0000 | 0.8000 | 4 |
| `binary_search` | 0.8571 | 0.7500 | 0.8000 | 8 |
| `recursion` | 0.3571 | 0.6250 | 0.4545 | 16 |
| `complexity` | 0.9359 | 0.9241 | 0.9299 | 79 |
| `data_structures` | 0.4577 | 0.8553 | 0.5963 | 152 |
| `algorithms` | 0.9468 | 0.9822 | 0.9642 | 507 |

## 3. Taxonomy Mapping Layer

The mapping layer converts raw competitive programming tags from TACO (`'Dynamic programming'`, `'Segment trees revisited'`, `'Range queries'`, `'Spanning trees'`, etc.) and problem text signals into the 21 canonical skills for Interview-ai-er.
This prevents raw competitive programming tag pollution while preserving algorithmic semantics.
