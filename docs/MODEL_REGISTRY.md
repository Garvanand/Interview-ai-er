# Interview AI Model Registry

This document serves as the authoritative, human-readable model registry for the Interview AI platform. It tracks model lineage, active and retired versions, datasets, training runs, artifact hashes, evaluation benchmarks, and database persistence guarantees.

A machine-readable version of this registry is available at [`ml/model_registry.json`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/model_registry.json).

---

## 1. Core Principles & Immutability Guarantees

Every AI and machine learning inference executed by the platform and stored in the database is strictly attributable to a specific, version-controlled model release.

### Persistent Inference Attribution Schema
Whenever an inference is generated (whether for difficulty estimation, question skill tagging, candidate answer evaluation, code defect analysis, or latent mastery updating), the following five fields are immutably persisted alongside the result:

| Metadata Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `model_name` | `VARCHAR(100)` | Canonical model identifier | `question-difficulty-v1`, `answer-nli-v1` |
| `model_version` | `VARCHAR(50)` | Semantic version of the trained weights/rules | `1.1.0`, `1.0.0` |
| `dataset_version` | `VARCHAR(100)` | Identifier & version tag of the training corpus | `2026.10`, `mnli-snli-v1`, `EdNet-KT1-v1` |
| `training_run` | `VARCHAR(150)` | Unique training execution run ID | `question-difficulty-v1_20261003T063825Z` |
| `inference_timestamp` | `TIMESTAMPTZ` | ISO 8601 UTC timestamp of inference execution | `2026-10-03T06:38:25.123456+00:00` |

### Immutability & Historical Interpretability
1. **Zero Overwrite Rule**: Historical interview evaluations stored in the database are **immutable**. When candidate answers or code submissions are evaluated, the resulting record and its attribution metadata are inserted into append-only storage.
2. **New Model Deployment Isolation**: Deploying a newer model (e.g., upgrading from `1.1.0` to `2.0.0`) **never mutates or overwrites historical evaluations**.
3. **Continuous Interpretability**: Historical evaluations remain 100% interpretable even years after an older model version has been retired. The registry permanently preserves previous model configurations, evaluation metrics, and artifact references.
4. **Re-evaluation Versioning**: If an existing candidate response is re-evaluated under a newer model release, the new evaluation is recorded as a separate record in `evaluation_history` with the new model version, leaving the original historical evaluation intact.

---

## 2. Active Model Catalog Matrix

| Model Identifier | Capability / Task | Category | Base Architecture | Active Version | Dataset & Version | Training Run ID | Artifact Hash | Status | Latency SLA |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`question-difficulty-v1`** | Question Difficulty Classification | `TRAINED BY US` | TF-IDF + Logistic Regression / MiniLM | `1.1.0` | `BAAI/TACO + codeparrot/apps` (`2026.10`) | `question-difficulty-v1_20261003T063825Z` | `12ef38983aa0...` | **Active** | < 25 ms |
| **`question-skill-v1`** | Multi-Label Skill Tagging | `TRAINED BY US` | TF-IDF + OneVsRest Logistic Regression | `1.1.0` | `BAAI/TACO` (`2026.10`) | `question-skill-tagger-v1_20261003T063901Z` | `ad21e4620e35...` | **Active** | < 20 ms |
| **`answer-nli-v1`** | Rubric Concept Coverage (NLI) | `PRETRAINED` | DeBERTa-v3 Cross-Encoder + MiniLM | `1.0.0` | `MNLI + SNLI` (`mnli-snli-v1`) | `answer-nli-v1_pretrained_deberta_minilm` | `deberta_v3_nli...` | **Active** | < 150 ms |
| **`code-risk-v1`** | Code Defect / Vulnerability Risk | `FINE-TUNED BY US` | Microsoft CodeBERT-base | `1.0.0` | `CodeXGLUE Defect` (`CodeXGLUE-defect-v1`) | `code-risk-v1_codebert_ast_analysis` | `codebert_defect...` | **Active** | < 180 ms |
| **`mastery-v1`** | Candidate Skill Mastery | `TRAINED BY US` | 2-Parameter Logistic IRT (2PL-IRT) | `1.0.0` | `mgor/EDNet` (`EdNet-KT1-v1`) | `mastery-v1_2pl_irt_calibration` | `irt_2pl_ednet...` | **Active** | < 2 ms |

---

## 3. Detailed Model Specifications

### 3.1 `question-difficulty-v1`

* **Task**: Multiclass classification predicting whether an interview question is `beginner`, `intermediate`, or `advanced`.
* **Category**: `TRAINED BY US`
* **Artifact Location**: [`ml/artifacts/difficulty/difficulty_model.joblib`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/artifacts/difficulty/difficulty_model.joblib)
* **Metadata Record**: [`ml/artifacts/difficulty/training_metadata.json`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/artifacts/difficulty/training_metadata.json)
* **Dataset**: BAAI/TACO + codeparrot/apps (1,500 curated, de-duplicated samples; stratified 70/10/20 split)
* **Preprocessing**: Text normalization, code block preservation, sublinear TF-IDF (1-2 grams, max 5,000 features).
* **Hyperparameters**:
  * Logistic Regression: `C=1.0`, `solver='lbfgs'`, `class_weight='balanced'`, `max_iter=1000`, multinomial.
* **Empirical Benchmark Metrics**:
  * Validation Accuracy: **55.33%** | Validation Macro F1: **0.5465**
  * Test Accuracy: **65.67%** | Test Macro F1: **0.6558** | Test Weighted F1: **0.6555**
  * Test Per-Class F1: Beginner (**0.6526**), Intermediate (**0.6421**), Advanced (**0.6727**)
* **Fallback Strategy**:
  1. *Primary ML*: Trained TF-IDF + Logistic Regression / Transformer classifier (`source="ml"`)
  2. *Secondary Model*: Pretrained MiniLM embedding prototype cosine similarity (`source="pretrained"`)
  3. *Tier 3 LLM*: Gemini structured difficulty reasoning (`source="llm"`)
  4. *Safety Net*: Deterministic lexical heuristic (`source="deterministic"`)
* **Version History**:
  * `1.1.0` (Active): Trained on full stratified TACO + APPS corpus with leakage prevention.
  * `1.0.0` (Retired): Baseline classical TF-IDF model without stratified APPS augmentation.

---

### 3.2 `question-skill-v1`

* **Task**: Multi-label classification categorizing questions across 21 canonical technical skills (e.g., dynamic programming, graphs, trees, recursion, hashing).
* **Category**: `TRAINED BY US`
* **Artifact Location**: [`ml/artifacts/skill_tagger/skill_classifier.joblib`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/artifacts/skill_tagger/skill_classifier.joblib)
* **Metadata Record**: [`ml/artifacts/skill_tagger/training_metadata.json`](file:///c:/Users/GARV%20ANAND/Downloads/Krish%20project/Interview-ai-er/ml/artifacts/skill_tagger/training_metadata.json)
* **Dataset**: BAAI/TACO (2,600 samples across 21 technical taxonomy labels, stratified train/val/test).
* **Preprocessing**: Sublinear TF-IDF vectorizer (max 6,000 features, 1-2 n-grams, English stop words removed).
* **Hyperparameters**:
  * `OneVsRestClassifier(LogisticRegression(C=2.0, class_weight='balanced', solver='lbfgs', max_iter=1000))`
  * Prediction threshold: `0.30`, minimum 1 label guaranteed per question.
* **Empirical Benchmark Metrics**:
  * Validation Micro F1: **0.6487** | Validation Macro F1: **0.6020** | Hamming Loss: **0.0907**
  * Test Micro F1: **0.6453** | Test Macro F1: **0.4994** | Hamming Loss: **0.0962**
  * Test Micro Recall: **0.8652**
* **Fallback Strategy**:
  1. *Primary ML*: Trained multi-label OneVsRest classifier (`source="ml"`)
  2. *Safety Net*: Deterministic 21-skill keyword regex taxonomy parser (`source="deterministic"`)
* **Version History**:
  * `1.1.0` (Active): Full 21-label taxonomy with balanced regularization and leakage checks.
  * `1.0.0` (Retired): Initial prototype with 12 basic tags.

---

### 3.3 `answer-nli-v1`

* **Task**: Natural Language Inference (NLI) evaluating candidate answer coverage against rubric concepts.
* **Category**: `PRETRAINED`
* **Base Architecture**: `cross-encoder/nli-deberta-v3-base` + `sentence-transformers/all-MiniLM-L6-v2`
* **Dataset**: Multi-Genre NLI (MNLI) + Stanford NLI (SNLI)
* **Scoring Formulation**:
  $$\text{Concept Score} = (0.65 \times \text{Entailment Probability}) + (0.35 \times \text{Semantic Cosine Similarity})$$
* **Thresholds**:
  * Covered: $\ge 0.60$
  * Partially Covered: $\ge 0.35$
  * Contradicted: Contradiction probability $\ge 0.50$
* **Fallback Strategy**:
  1. *Primary ML*: DeBERTa-v3 cross-encoder + MiniLM dense similarity (`source="ml"`)
  2. *Secondary Model*: MiniLM embedding cosine similarity alone (`source="pretrained"`)
  3. *Tier 3 LLM*: Gemini structured rubric concept evaluation (`source="llm"`)
  4. *Safety Net*: Deterministic lexical overlap heuristic (`source="deterministic"`)

---

### 3.4 `code-risk-v1`

* **Task**: Sequence classification detecting defects, algorithmic vulnerabilities, and edge-case risks in submitted code.
* **Category**: `FINE-TUNED BY US`
* **Base Architecture**: `microsoft/codebert-base` with sequence classification head
* **Dataset**: CodeXGLUE Defect Detection corpus
* **Risk Bands**:
  * Low Risk: Probability $< 0.30$
  * Medium Risk: $0.30 \le \text{Probability} < 0.65$
  * High Risk: Probability $\ge 0.65$
* **Signal Disclaimer**:
  > *This is an ML-derived code-risk signal, not proof of incorrectness. Executable sandbox tests remain authoritative for runtime execution correctness.*
* **Fallback Strategy**:
  1. *Primary ML*: Fine-tuned CodeBERT model weights (`source="ml"`)
  2. *Secondary Model*: Pretrained base CodeBERT (`source="pretrained"`)
  3. *Safety Net*: Deterministic AST feature extractor & static analysis (`source="deterministic"`)

---

### 3.5 `mastery-v1`

* **Task**: Dynamic probabilistic candidate skill mastery and latent ability estimation.
* **Category**: `TRAINED BY US`
* **Foundational Framework**: Two-Parameter Logistic Item Response Theory (2PL-IRT) / Bayesian Knowledge Tracing.
* **Dataset**: Calibrated via `mgor/EDNet` student interaction distributions.
* **Mathematical Formulation**:
  $$P(Y = 1 \mid \theta) = \frac{1}{1 + e^{-a(\theta - b)}}$$
  where:
  * $\theta \in [-3.0, +3.0]$ is candidate latent ability.
  * $b \in \{-1.2, 0.0, +1.4\}$ is question difficulty prior (beginner, intermediate, advanced).
  * $a = 1.2$ is item discrimination factor.
* **Proficiency Conversion**:
  $$\text{Proficiency}_{100} = \frac{\theta + 3.0}{6.0} \times 100$$
* **Update Rule**: Maximum A Posteriori (MAP) stochastic gradient step with learning rate $\eta = 0.35$:
  $$\theta_{t+1} = \text{clamp}\Big(\theta_t + \eta \cdot (y - P) \cdot a, -3.0, +3.0\Big)$$

---

## 4. Database Schema Integration

The platform relational schema defines explicit columns and tables for model attribution:

```sql
-- 1. Evaluated Candidate Answers & Code Submissions
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    response_id UUID REFERENCES responses(id) ON DELETE CASCADE,
    score DECIMAL(5,2),
    feedback TEXT,
    evaluation_details JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'COMPLETED',
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    dataset_version VARCHAR(100),
    training_run VARCHAR(150),
    inference_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. ML-Derived Question Skill Predictions
CREATE TABLE IF NOT EXISTS question_skill_predictions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    question_id UUID REFERENCES interview_questions(id) ON DELETE CASCADE,
    predicted_skills JSONB NOT NULL,
    confidence DECIMAL(5,4) DEFAULT 0.0000,
    model_name VARCHAR(100) DEFAULT 'question-skill-v1',
    model_version VARCHAR(100) NOT NULL,
    dataset_version VARCHAR(100) DEFAULT '2026.10',
    training_run VARCHAR(150) DEFAULT 'question-skill-tagger-v1_20261003T063901Z',
    inference_timestamp TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Dedicated Platform-Wide Model Inference Log (Immutable)
CREATE TABLE IF NOT EXISTS model_inferences (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE SET NULL,
    question_id UUID REFERENCES interview_questions(id) ON DELETE SET NULL,
    response_id UUID REFERENCES responses(id) ON DELETE SET NULL,
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    dataset_version VARCHAR(100) NOT NULL,
    training_run VARCHAR(150) NOT NULL,
    inference_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    inference_output JSONB DEFAULT '{}',
    source VARCHAR(50) DEFAULT 'ml',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 5. Lifecycle Governance & Version Upgrades

When a new model is trained and deployed:
1. **Offline Training**: The offline training pipeline generates artifacts and metadata with verified metrics in `ml/artifacts/<task>/`.
2. **Registry Registration**: The new model is registered via `ModelVersionRegistry.deploy_new_version(...)` or directly in `ml/model_registry.json`.
3. **Historical Preservation**: The former active version is moved to `previous_versions` with `status: "retired"` and `retired_at` timestamp.
4. **Historical Immunity**: Existing rows in `evaluations`, `question_skill_predictions`, and `model_inferences` are **never updated**. Queries on historical sessions retrieve the exact model version used at that time.
5. **Transparency**: Evaluation detail JSON payloads contain `model_attribution` blocks displaying exact version and dataset provenance for audits.
