# ML Model Registry

This document catalogs all machine learning models used in the Interview-ai-er system.

## 1. Question Difficulty Predictor
* **Purpose**: Predicts the cognitive complexity and expected difficulty band of a generated interview question.
* **Dataset**: `leetcode-questions` / `hackerrank-prompts` (Synthetic subset)
* **Dataset License**: MIT / Custom Internal
* **Pretrained Base**: `all-MiniLM-L6-v2` (SentenceTransformers)
* **Training Method**: Zero-shot similarity / Heuristic rule-based fallback
* **Task**: Difficulty Classification (Bands 1-5)
* **Metrics**: Accuracy (Heuristic evaluation)
* **Limitations**: Heavily biased toward keywords (e.g., "easy", "hard"); fails to detect implicit complexity in novel prompts.
* **Inference Latency**: ~5-15ms
* **Artifact Version**: v1.0.0

## 2. Skill Tagger (SkillClassifier)
* **Purpose**: Categorizes arbitrary interview questions into predefined skill buckets (e.g., "trees", "databases").
* **Dataset**: Custom SWE Interview Taxonomy dataset
* **Dataset License**: MIT
* **Pretrained Base**: `all-MiniLM-L6-v2`
* **Training Method**: Zero-shot cosine similarity mapping to skill centroids
* **Task**: Multi-class text classification
* **Metrics**: Accuracy
* **Limitations**: Struggles with hybrid questions requiring multiple distinct skills (currently returns top-1 mostly).
* **Inference Latency**: ~5-10ms
* **Artifact Version**: v1.0.0

## 3. Answer Analyzer (ConceptCoverageModel)
* **Purpose**: Assesses candidate responses to verify if specific technical concepts were covered.
* **Dataset**: None (Zero-shot)
* **Dataset License**: N/A
* **Pretrained Base**: `all-MiniLM-L6-v2`
* **Training Method**: Zero-shot semantic textual similarity (STS)
* **Task**: Semantic Concept Matching
* **Metrics**: Mean Absolute Error (MAE) on coverage score
* **Limitations**: Highly sensitive to phrasing; struggles to identify conceptually correct answers that use completely different metaphors.
* **Inference Latency**: ~10-20ms
* **Artifact Version**: v1.0.0

## 4. Code Model (CodeDefectDetector)
* **Purpose**: Identifies potential defects, vulnerabilities, or bad practices in candidate code.
* **Dataset**: `microsoft/CodeXGLUE` (Defect-detection)
* **Dataset License**: Computational Use Only (Non-Commercial Research)
* **Pretrained Base**: `microsoft/codebert-base`
* **Training Method**: Fine-tuning classification head
* **Task**: Defect Detection / Binary Classification
* **Metrics**: Accuracy, F1-Score
* **Limitations**: Focuses mostly on syntax patterns rather than deep logical errors; high false positive rate for partial code snippets.
* **Inference Latency**: ~30-50ms (Transformer fallback)
* **Artifact Version**: v1.0.0

## 5. Mastery Model (BayesianKnowledgeTracing)
* **Purpose**: Estimates sequential skill mastery based on candidate attempt history over time.
* **Dataset**: `mgor/EDNet` (For prototyping and validation only)
* **Dataset License**: CC BY-NC-SA 4.0
* **Pretrained Base**: None (Bayesian sequential model)
* **Training Method**: Heuristic / EM Calibration (Planned)
* **Task**: Sequential Proficiency Estimation
* **Metrics**: Deterministic Update Accuracy
* **Limitations**: Does not capture forgetting curves; treats all skills as independent (no skill-to-skill knowledge transfer).
* **Inference Latency**: ~1-5ms
* **Artifact Version**: v1.0.0
