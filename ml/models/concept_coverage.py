"""
Transformer-based Answer Concept Coverage Model.
Category: PRETRAINED (cross-encoder/nli-deberta-v3-base + sentence-transformers/all-MiniLM-L6-v2).

Evaluates whether candidate responses logically cover required technical concepts
using Natural Language Inference (NLI) zero-shot cross-encoders and semantic
embedding similarity.

Pipeline:
    Candidate Answer
    ↓  MiniLM semantic embedding (per-concept similarity)
    ↓  DeBERTa NLI cross-encoder (per-concept entailment/contradiction/neutral)
    ↓  Deterministic aggregation formula
    ↓  Structured evidence output

This produces an "ML-derived concept coverage signal" — NOT a scientifically
validated interview score.  The signal is consumed by the Gemini evaluator as
structured evidence so that Gemini explains the evidence rather than inventing
its own.

Aggregation Formula (documented & deterministic):
──────────────────────────────────────────────────
For each concept c_i:
    concept_score_i = (w_nli * entailment_prob_i) + (w_sim * semantic_similarity_i)
    where w_nli = 0.65, w_sim = 0.35  (NLI is the stronger signal)

    status:
        "covered"       if concept_score_i >= 0.60
        "partially"     if 0.35 <= concept_score_i < 0.60
        "missing"       if concept_score_i < 0.35
        "contradicted"  if contradiction_prob_i >= 0.50

Overall coverage %:
    coverage_pct = mean(concept_score_i for all i) * 100
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Aggregation weights (documented — see module docstring)
W_NLI = 0.65
W_SIM = 0.35

# Status thresholds
COVERED_THRESHOLD = 0.60
PARTIAL_THRESHOLD = 0.35
CONTRADICTION_THRESHOLD = 0.50


class ConceptCoverageAnalyzer:
    """
    Hybrid DeBERTa-v3 NLI + MiniLM semantic similarity concept coverage analyzer.

    Produces per-concept evidence with full NLI probability triplets and semantic
    similarity scores, aggregated into an "ML-derived concept coverage signal".
    """

    def __init__(
        self,
        nli_model_name: str = DEFAULT_NLI_MODEL,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        device: str = "cpu",
    ):
        self.nli_model_name = nli_model_name
        self.embedding_model_name = embedding_model_name
        self.device = device
        self._nli_model = None
        self._embedding_model = None
        self._nli_fallback = False
        self._emb_fallback = False

    # ─── Lazy loading ──────────────────────────────────────────────

    def _load_nli_model(self):
        if self._nli_model is not None or self._nli_fallback:
            return
        try:
            from sentence_transformers import CrossEncoder
            logger.info(
                "Loading CrossEncoder NLI model: %s on %s",
                self.nli_model_name,
                self.device,
            )
            self._nli_model = CrossEncoder(self.nli_model_name, device=self.device)
        except Exception as e:
            logger.warning(
                "Could not load CrossEncoder (%s): %s. NLI will use lexical fallback.",
                self.nli_model_name,
                e,
            )
            self._nli_fallback = True

    def _load_embedding_model(self):
        if self._embedding_model is not None or self._emb_fallback:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(
                "Loading SentenceTransformer model: %s on %s",
                self.embedding_model_name,
                self.device,
            )
            self._embedding_model = SentenceTransformer(
                self.embedding_model_name, device=self.device
            )
        except Exception as e:
            logger.warning(
                "Could not load SentenceTransformer (%s): %s. Similarity will use lexical fallback.",
                self.embedding_model_name,
                e,
            )
            self._emb_fallback = True

    # ─── NLI inference ─────────────────────────────────────────────

    def _run_nli(
        self, candidate_answer: str, concepts: List[str]
    ) -> List[Dict[str, float]]:
        """
        Run NLI cross-encoder for each concept.
        Returns list of dicts with {contradiction, entailment, neutral} probabilities.

        For cross-encoder/nli-deberta-v3-base the label order is:
            [contradiction, entailment, neutral]
        """
        self._load_nli_model()

        if self._nli_model is not None and not self._nli_fallback:
            pairs = [
                (
                    candidate_answer,
                    f"The candidate correctly explains and addresses {concept}.",
                )
                for concept in concepts
            ]
            try:
                raw_scores = self._nli_model.predict(pairs, apply_softmax=True)
                results = []
                for probs in raw_scores:
                    probs_list = [float(p) for p in probs]
                    results.append({
                        "contradiction_probability": round(probs_list[0], 4),
                        "entailment_probability": round(probs_list[1], 4),
                        "neutral_probability": round(probs_list[2], 4),
                    })
                return results
            except Exception as e:
                logger.error("DeBERTa NLI inference failed: %s. Using fallback.", e)

        # ── Deterministic lexical fallback ──
        return self._lexical_nli_fallback(candidate_answer, concepts)

    def _lexical_nli_fallback(
        self, candidate_answer: str, concepts: List[str]
    ) -> List[Dict[str, float]]:
        """Deterministic word-overlap heuristic when transformer is unavailable."""
        answer_lower = candidate_answer.lower()
        results = []
        for concept in concepts:
            terms = [t.strip().lower() for t in concept.split() if len(t.strip()) > 3]
            if not terms:
                results.append({
                    "contradiction_probability": 0.10,
                    "entailment_probability": 0.40,
                    "neutral_probability": 0.50,
                })
                continue
            matches = sum(1 for term in terms if term in answer_lower)
            coverage_ratio = min(1.0, matches / len(terms))
            # Map coverage_ratio to pseudo-probabilities
            entailment = round(coverage_ratio * 0.85, 4)
            contradiction = round(max(0.0, (1.0 - coverage_ratio) * 0.15), 4)
            neutral = round(max(0.0, 1.0 - entailment - contradiction), 4)
            results.append({
                "contradiction_probability": contradiction,
                "entailment_probability": entailment,
                "neutral_probability": neutral,
            })
        return results

    # ─── Semantic similarity ───────────────────────────────────────

    def _compute_similarities(
        self, candidate_answer: str, concepts: List[str]
    ) -> List[float]:
        """
        Compute cosine similarity between candidate_answer embedding and
        each concept embedding using MiniLM.
        """
        self._load_embedding_model()

        if self._embedding_model is not None and not self._emb_fallback:
            try:
                all_texts = [candidate_answer] + [
                    f"The answer covers: {c}" for c in concepts
                ]
                embeddings = self._embedding_model.encode(
                    all_texts, normalize_embeddings=True, show_progress_bar=False
                )
                answer_emb = embeddings[0]
                sims = []
                for i in range(1, len(embeddings)):
                    sim = float(np.dot(answer_emb, embeddings[i]))
                    sims.append(round(max(0.0, min(1.0, sim)), 4))
                return sims
            except Exception as e:
                logger.error(
                    "MiniLM embedding inference failed: %s. Using fallback.", e
                )

        # ── Deterministic lexical fallback ──
        return self._lexical_similarity_fallback(candidate_answer, concepts)

    def _lexical_similarity_fallback(
        self, candidate_answer: str, concepts: List[str]
    ) -> List[float]:
        """Jaccard-like word overlap heuristic."""
        answer_words = set(candidate_answer.lower().split())
        sims = []
        for concept in concepts:
            concept_words = set(concept.lower().split())
            if not concept_words:
                sims.append(0.0)
                continue
            overlap = len(answer_words & concept_words)
            union = len(answer_words | concept_words)
            sims.append(round(overlap / union if union > 0 else 0.0, 4))
        return sims

    # ─── Status determination ──────────────────────────────────────

    @staticmethod
    def _determine_status(
        concept_score: float, contradiction_prob: float
    ) -> str:
        """
        Determine concept coverage status using documented thresholds.

        Priority: contradiction check first, then score-based thresholds.
        """
        if contradiction_prob >= CONTRADICTION_THRESHOLD:
            return "contradicted"
        if concept_score >= COVERED_THRESHOLD:
            return "covered"
        if concept_score >= PARTIAL_THRESHOLD:
            return "partially_covered"
        return "missing"

    # ─── Main evaluation entry point ───────────────────────────────

    def evaluate_concepts(
        self,
        candidate_answer: str,
        expected_concepts: List[str],
    ) -> Dict[str, Any]:
        """
        Full hybrid concept coverage evaluation.

        Returns structured evidence including per-concept NLI probabilities,
        semantic similarity, composite scores, and overall aggregation.

        This is an "ML-derived concept coverage signal" — NOT a scientifically
        validated interview score.
        """
        t0 = time.time()

        # Handle trivial cases
        if not expected_concepts:
            return {
                "overall_coverage_pct": 100.0,
                "concept_results": [],
                "covered_concepts": [],
                "missing_concepts": [],
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "method": "trivial_empty_rubric",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": "N/A (empty rubric)",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
            }

        if not candidate_answer or not candidate_answer.strip():
            empty_results = []
            for concept in expected_concepts:
                empty_results.append({
                    "concept": concept,
                    "entailment_probability": 0.0,
                    "contradiction_probability": 0.0,
                    "neutral_probability": 1.0,
                    "semantic_similarity": 0.0,
                    "concept_score": 0.0,
                    "status": "missing",
                })
            return {
                "overall_coverage_pct": 0.0,
                "concept_results": empty_results,
                "covered_concepts": [],
                "missing_concepts": list(expected_concepts),
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "method": "empty_answer",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": f"concept_score = ({W_NLI} * entailment) + ({W_SIM} * similarity)",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
            }

        # ── Step 1: NLI probability triplets ──
        nli_results = self._run_nli(candidate_answer, expected_concepts)

        # ── Step 2: Semantic similarity ──
        similarities = self._compute_similarities(candidate_answer, expected_concepts)

        # ── Step 3: Per-concept aggregation ──
        concept_results = []
        covered = []
        missing = []
        contradicted = []
        partially_covered = []

        method_parts = []
        if self._nli_model is not None and not self._nli_fallback:
            method_parts.append("deberta_v3_nli")
        else:
            method_parts.append("lexical_nli_fallback")
        if self._embedding_model is not None and not self._emb_fallback:
            method_parts.append("minilm_embedding")
        else:
            method_parts.append("lexical_similarity_fallback")

        for i, concept in enumerate(expected_concepts):
            nli = nli_results[i]
            sim = similarities[i]

            # Documented deterministic aggregation
            concept_score = round(
                (W_NLI * nli["entailment_probability"]) + (W_SIM * sim), 4
            )

            status = self._determine_status(
                concept_score, nli["contradiction_probability"]
            )

            result_entry = {
                "concept": concept,
                "entailment_probability": nli["entailment_probability"],
                "contradiction_probability": nli["contradiction_probability"],
                "neutral_probability": nli["neutral_probability"],
                "semantic_similarity": sim,
                "concept_score": concept_score,
                "status": status,
            }
            concept_results.append(result_entry)

            if status == "covered":
                covered.append(concept)
            elif status == "missing":
                missing.append(concept)
            elif status == "contradicted":
                contradicted.append(concept)
            elif status == "partially_covered":
                partially_covered.append(concept)

        # ── Step 4: Overall coverage ──
        all_scores = [r["concept_score"] for r in concept_results]
        overall_pct = round((sum(all_scores) / len(all_scores)) * 100.0, 1)

        inference_ms = round((time.time() - t0) * 1000, 2)

        return {
            "overall_coverage_pct": overall_pct,
            "concept_results": concept_results,
            "covered_concepts": covered,
            "missing_concepts": missing,
            "contradicted_concepts": contradicted,
            "partially_covered_concepts": partially_covered,
            "method": "+".join(method_parts),
            "signal_type": "ml_derived_concept_coverage_signal",
            "aggregation_formula": f"concept_score = ({W_NLI} * entailment) + ({W_SIM} * similarity)",
            "inference_time_ms": inference_ms,
        }

    # ─── Concept extraction helper ─────────────────────────────────

    @staticmethod
    def extract_concepts_from_rubric(evaluation_rubric: str) -> List[str]:
        """
        Extract testable concept statements from a question's evaluation rubric.

        Splits on common delimiters (newlines, bullet points, numbered lists,
        semicolons) and filters out short noise fragments.
        """
        import re

        if not evaluation_rubric or not evaluation_rubric.strip():
            return []

        # Split on common rubric delimiters
        lines = re.split(r'[\n;]|(?:\d+\.)|(?:[-•*]\s)', evaluation_rubric)
        concepts = []
        for line in lines:
            cleaned = line.strip().rstrip('.')
            # Keep only substantive phrases (>15 chars, >2 words)
            if len(cleaned) > 15 and len(cleaned.split()) > 2:
                concepts.append(cleaned)

        return concepts[:20]  # Cap at 20 concepts to bound inference cost
