# Machine Learning Model Registry

This registry tracks all machine learning models, representations, probabilistic engines, and deterministic baselines utilized in the Interview Intelligence Platform.

---

## Model Inventory & Specification Table

| Model ID | Capability | Category | Base Architecture / Pretrained Source | Target Hardware | Expected Latency | Artifact Location | Target Evaluation Metric (Non-Fabricated) |
|---|---|---|---|---|---|---|---|
| `question-difficulty-v1` | Question Difficulty Prediction | **TRAINED BY US** | `all-MiniLM-L6-v2` + Ridge / Logistic Regression Head | CPU | 15–30 ms | `ml/models/weights/difficulty_model.joblib` | Macro-F1 $\ge 0.72$, Accuracy on 3-class TACO test split |
| `question-skill-classifier-v1` | Question Skill / Topic Classification | **TRAINED BY US** | `all-MiniLM-L6-v2` + MultiOutputClassifier | CPU | 15–25 ms | `ml/models/weights/skill_classifier.joblib` | Multi-label Micro-F1 $\ge 0.78$ on TACO topic tags |
| `answer-concept-coverage-v1` | Transformer Answer Concept Coverage | **PRETRAINED** | `cross-encoder/nli-deberta-v3-base` | CPU or GPU | 80–180 ms | HuggingFace Hub Cache (`~/.cache/huggingface`) | Expected Calibration Error (ECE) $< 0.12$ on technical rubrics |
| `semantic-answer-similarity-v1` | Semantic Answer Similarity | **PRETRAINED** | `sentence-transformers/all-MiniLM-L6-v2` | CPU | 10–20 ms | HuggingFace Hub Cache (`~/.cache/huggingface`) | Cosine correlation $\ge 0.82$ against reference explanations |
| `code-defect-detector-v1` | Code Defect / Vulnerability Risk | **FINE-TUNED BY US** | `microsoft/codebert-base` (SequenceClassification Head) | GPU (Train), CPU (Infer) | 100–250 ms | `ml/models/weights/codebert_defect/` | Binary Accuracy $\ge 0.65$, ROC-AUC $\ge 0.70$ on CodeXGLUE Devign |
| `voice-stt-whisper-v1` | Speech-to-Text for Voice Interviews | **PRETRAINED** | `openai/whisper-base.en` (`faster-whisper` INT8) | CPU or GPU | 300–600 ms | HuggingFace / CTranslate2 Model Cache | Word Error Rate (WER) $< 12\%$ on technical conversational English |
| `candidate-skill-mastery-irt-v1` | Candidate Skill Mastery Modeling | **TRAINED BY US** | Two-Parameter Logistic Item Response Theory (2PL-IRT) | CPU | < 2 ms | In-memory algorithm / `app/services/supabase_service.py` | Calibration log-likelihood on EdNet interaction sequences |
| `adaptive-question-selector-v1` | ML-Assisted Adaptive Question Selection | **TRAINED BY US** / **DETERMINISTIC** | Computerized Adaptive Testing (Fisher Information CAT) | CPU | < 5 ms | In-memory algorithm / `ml/models/adaptive_selector.py` | Information gain efficiency: $\ge 25\%$ reduction in questions to reach stable $\theta$ confidence |

---

## Detailed Model Cards

### 1. `question-difficulty-v1`
- **Capability**: Predicts question complexity (`beginner`, `intermediate`, `advanced`).
- **Category**: `TRAINED BY US`
- **Input**: Raw question text string.
- **Output**: Categorical label + probability distribution over 3 difficulty tiers.
- **Training Pipeline**: [`ml/training/train_difficulty.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/training/train_difficulty.py)
- **Datasets**: BAAI/TACO + codeparrot/apps.
- **Status**: Code complete; fallback heuristic active pending offline weight generation.

### 2. `question-skill-classifier-v1`
- **Capability**: Identifies primary and secondary technical skills from question statements.
- **Category**: `TRAINED BY US`
- **Input**: Question prompt.
- **Output**: Top $k$ canonical skill tags with confidence scores.
- **Training Pipeline**: [`ml/training/train_skill_classifier.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/training/train_skill_classifier.py)
- **Datasets**: BAAI/TACO tags.
- **Status**: Code complete; regex keyword taxonomy fallback active.

### 3. `answer-concept-coverage-v1`
- **Capability**: Cross-encoder zero-shot NLI verifying whether expected concepts were explained.
- **Category**: `PRETRAINED`
- **Model**: `cross-encoder/nli-deberta-v3-base` (86M parameters).
- **Inference Module**: [`ml/models/concept_coverage.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/concept_coverage.py)
- **Status**: Verified working with lexical keyword coverage fallback.

### 4. `semantic-answer-similarity-v1`
- **Capability**: Dense sentence embeddings for similarity search and drift detection.
- **Category**: `PRETRAINED`
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (22M parameters, 384 dimensions).
- **Inference Module**: [`ml/features/text_embeddings.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/features/text_embeddings.py)
- **Status**: Fully functional with deterministic hash fallback.

### 5. `code-defect-detector-v1`
- **Capability**: Fast static risk scoring before sandbox code execution.
- **Category**: `FINE-TUNED BY US`
- **Base Model**: `microsoft/codebert-base` (125M parameters).
- **Training Pipeline**: [`ml/training/train_defect_detector.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/training/train_defect_detector.py)
- **Dataset**: Microsoft CodeXGLUE defect detection benchmark.
- **Status**: Pipeline designed; marked as optional in production runtime.

### 6. `voice-stt-whisper-v1`
- **Capability**: Voice answer audio transcription.
- **Category**: `PRETRAINED`
- **Model**: `openai/whisper-base.en` (74M parameters).
- **Inference Module**: [`ml/models/speech_to_text.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/speech_to_text.py)
- **Status**: Implemented with faster-whisper CTranslate2 support; optional for text-only clients.

### 7. `candidate-skill-mastery-irt-v1`
- **Capability**: Item Response Theory (2PL-IRT) latent ability estimation.
- **Category**: `TRAINED BY US`
- **Mathematical Engine**: [`ml/models/skill_mastery.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/skill_mastery.py)
- **Dataset Foundation**: mgor/EDNet interaction curves.
- **Status**: Tested and verified (100% deterministic at inference time).

### 8. `adaptive-question-selector-v1`
- **Capability**: Computerized Adaptive Testing question selection via Fisher Information.
- **Category**: `TRAINED BY US` / `DETERMINISTIC`
- **Implementation**: [`ml/models/adaptive_selector.py`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/models/adaptive_selector.py)
- **Status**: Tested and verified (sub-millisecond execution).

---

## Non-Fabrication Notice

> [!IMPORTANT]
> In accordance with project engineering standards, accuracy percentages and benchmark numbers above represent **Target Evaluation Criteria** to be empirically validated during Phase 2 training on full dataset shards. No synthetic or fabricated test metrics are claimed as historical fact.
