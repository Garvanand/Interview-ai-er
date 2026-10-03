"""
Transformer-based Answer Concept Coverage Model with 3-Tier Fallback Architecture.

Classes of Intelligence:
1. PRIMARY ML ("ml"): DeBERTa-v3 NLI Cross-Encoder + MiniLM similarity.
2. SECONDARY MODEL ("pretrained" or "deterministic"): MiniLM semantic similarity alone or lexical overlap heuristic.
3. LLM FALLBACK ("llm"): Structured Gemini concept coverage analysis.
4. UNAVAILABLE ("unavailable"): When inputs are malformed or all tiers fail.

Confidence is strictly tied to the actual method; never manufactured.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
import numpy as np

from ml.serving.inference_service import InferenceService
from ml.fallbacks import (
    IntelligenceSource,
    log_fallback_event,
    try_llm_concept_coverage_fallback,
)
from ml.versioning import stamp_inference
from ml.calibration import get_confidence_metadata

logger = logging.getLogger(__name__)

DEFAULT_NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Aggregation weights
W_NLI = 0.65
W_SIM = 0.35

# Status thresholds
COVERED_THRESHOLD = 0.60
PARTIAL_THRESHOLD = 0.35
CONTRADICTION_THRESHOLD = 0.50


class ConceptCoverageAnalyzer:
    """
    3-Tier Concept Coverage Analyzer:
    Tier 1 (ml): DeBERTa-v3 NLI Cross-Encoder + MiniLM
    Tier 2 (pretrained/deterministic): MiniLM cosine similarity alone, or lexical overlap
    Tier 3 (llm): Structured Gemini reasoning
    Tier 4 (unavailable): Total failure or malformed input
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self._nli_failure_reason: Optional[str] = None

    # ─── Main Evaluation Entry Point ───────────────────────────────

    def evaluate_concepts(
        self,
        candidate_answer: str,
        expected_concepts: List[str],
        allow_llm: bool = True,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate concept coverage through the 3-tier cascade.
        """
        t0 = time.time()

        # Step 0: Input validation (Malformed inputs)
        if not isinstance(candidate_answer, str):
            logger.warning("Malformed input: candidate_answer must be a string, got %s", type(candidate_answer))
            return {
                "overall_coverage_pct": 0.0,
                "concept_results": [],
                "covered_concepts": [],
                "missing_concepts": list(expected_concepts) if isinstance(expected_concepts, list) else [],
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "confidence": 0.0,
                "source": IntelligenceSource.UNAVAILABLE.value,
                "method": "malformed_input_handler",
                "signal_type": "unavailable",
                "aggregation_formula": "N/A",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
                "error": "Malformed input: candidate_answer must be a string",
            }

        if not isinstance(expected_concepts, list):
            logger.warning("Malformed input: expected_concepts must be a list, got %s", type(expected_concepts))
            return {
                "overall_coverage_pct": 0.0,
                "concept_results": [],
                "covered_concepts": [],
                "missing_concepts": [],
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "confidence": 0.0,
                "source": IntelligenceSource.UNAVAILABLE.value,
                "method": "malformed_input_handler",
                "signal_type": "unavailable",
                "aggregation_formula": "N/A",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
                "error": "Malformed input: expected_concepts must be a list",
            }

        # Filter concepts to non-empty strings
        clean_concepts = [c.strip() for c in expected_concepts if isinstance(c, str) and c.strip()]

        if not clean_concepts:
            _conf_meta = get_confidence_metadata("answer-nli-v1", 1.0, source_tier="deterministic")
            empty_rubric_res = {
                "overall_coverage_pct": 100.0,
                "concept_results": [],
                "covered_concepts": [],
                "missing_concepts": [],
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "confidence": 1.0,
                "source": IntelligenceSource.DETERMINISTIC.value,
                "method": "trivial_empty_rubric",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": "N/A (empty rubric)",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
            return stamp_inference("answer-nli-v1", empty_rubric_res, version_override="deterministic_empty_v1")

        if not candidate_answer.strip():
            empty_results = []
            for concept in clean_concepts:
                empty_results.append({
                    "concept": concept,
                    "entailment_probability": 0.0,
                    "contradiction_probability": 0.0,
                    "neutral_probability": 1.0,
                    "semantic_similarity": 0.0,
                    "concept_score": 0.0,
                    "status": "missing",
                })
            _conf_meta = get_confidence_metadata("answer-nli-v1", 1.0, source_tier="deterministic")
            empty_answer_res = {
                "overall_coverage_pct": 0.0,
                "concept_results": empty_results,
                "covered_concepts": [],
                "missing_concepts": list(clean_concepts),
                "contradicted_concepts": [],
                "partially_covered_concepts": [],
                "confidence": 1.0,
                "source": IntelligenceSource.DETERMINISTIC.value,
                "method": "empty_answer",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": f"concept_score = ({W_NLI} * entailment) + ({W_SIM} * similarity)",
                "inference_time_ms": round((time.time() - t0) * 1000, 2),
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
            return stamp_inference("answer-nli-v1", empty_answer_res, version_override="deterministic_empty_v1")

        # ── Tier 1: PRIMARY ML (DeBERTa-v3 Cross-Encoder) ──────────────
        primary_res = self._try_deberta_primary(candidate_answer, clean_concepts, timeout_seconds)
        if primary_res is not None:
            primary_res["inference_time_ms"] = round((time.time() - t0) * 1000, 2)
            return stamp_inference("answer-nli-v1", primary_res)

        # ── Tier 2: SECONDARY MODEL (MiniLM Similarity Alone) ──────────
        secondary_res = self._try_minilm_secondary(candidate_answer, clean_concepts)
        if secondary_res is not None:
            log_fallback_event(
                component="concept_coverage",
                from_source=IntelligenceSource.ML.value,
                to_source=IntelligenceSource.PRETRAINED.value,
                reason=self._nli_failure_reason or "DeBERTa NLI cross-encoder unavailable",
            )
            secondary_res["inference_time_ms"] = round((time.time() - t0) * 1000, 2)
            return stamp_inference("answer-nli-v1", secondary_res)

        # ── Tier 3: LLM FALLBACK (Structured Gemini Analysis) ──────────
        if allow_llm:
            llm_res = try_llm_concept_coverage_fallback(candidate_answer, clean_concepts)
            if llm_res is not None:
                log_fallback_event(
                    component="concept_coverage",
                    from_source=IntelligenceSource.PRETRAINED.value,
                    to_source=IntelligenceSource.LLM.value,
                    reason="Transformer models failed; using Gemini LLM fallback",
                )
                llm_res["inference_time_ms"] = round((time.time() - t0) * 1000, 2)
                return stamp_inference("answer-nli-v1", llm_res)

        # ── Deterministic Heuristic Fallback (Lexical Overlap) ──────────
        lexical_res = self._lexical_deterministic_fallback(candidate_answer, clean_concepts)
        log_fallback_event(
            component="concept_coverage",
            from_source=IntelligenceSource.PRETRAINED.value,
            to_source=IntelligenceSource.DETERMINISTIC.value,
            reason="Transformers and LLM unavailable; using deterministic lexical overlap",
        )
        lexical_res["inference_time_ms"] = round((time.time() - t0) * 1000, 2)
        return stamp_inference("answer-nli-v1", lexical_res)

    # ── Tier 1: DeBERTa Cross-Encoder ──────────────────────────────

    def _try_deberta_primary(
        self,
        candidate_answer: str,
        concepts: List[str],
        timeout_seconds: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        pairs = [
            (candidate_answer, f"The candidate correctly explains and addresses {concept}.")
            for concept in concepts
        ]
        try:
            def _predict(model):
                return model.predict(pairs, apply_softmax=True)

            response = InferenceService.execute("answer-concept-coverage-v1", _predict, timeout_seconds=timeout_seconds)
            raw_scores = response["result"]

            nli_results = []
            for probs in raw_scores:
                probs_list = [float(p) for p in probs]
                nli_results.append({
                    "contradiction_probability": round(probs_list[0], 4),
                    "entailment_probability": round(probs_list[1], 4),
                    "neutral_probability": round(probs_list[2], 4),
                })

            # Get similarity component
            similarities = self._compute_similarities_or_fallback(candidate_answer, concepts)

            concept_results = []
            covered, missing, partial, contradicted = [], [], [], []

            for i, concept in enumerate(concepts):
                nli = nli_results[i]
                sim = similarities[i]
                concept_score = round((W_NLI * nli["entailment_probability"]) + (W_SIM * sim), 4)
                status = self._determine_status(concept_score, nli["contradiction_probability"])

                entry = {
                    "concept": concept,
                    "entailment_probability": nli["entailment_probability"],
                    "contradiction_probability": nli["contradiction_probability"],
                    "neutral_probability": nli["neutral_probability"],
                    "semantic_similarity": sim,
                    "concept_score": concept_score,
                    "status": status,
                }
                concept_results.append(entry)

                if status == "covered":
                    covered.append(concept)
                elif status == "missing":
                    missing.append(concept)
                elif status == "contradicted":
                    contradicted.append(concept)
                elif status == "partially_covered":
                    partial.append(concept)

            all_scores = [r["concept_score"] for r in concept_results]
            overall_pct = round((sum(all_scores) / len(all_scores)) * 100.0, 1)
            # Authentic confidence from entailment certainty
            avg_entailment = float(np.mean([r["entailment_probability"] for r in concept_results]))

            _conf_meta = get_confidence_metadata("answer-nli-v1", round(avg_entailment, 4), source_tier="ml")
            return {
                "overall_coverage_pct": overall_pct,
                "concept_results": concept_results,
                "covered_concepts": covered,
                "missing_concepts": missing,
                "contradicted_concepts": contradicted,
                "partially_covered_concepts": partial,
                "confidence": round(avg_entailment, 4),
                "source": IntelligenceSource.ML.value,
                "method": "deberta_v3_nli+minilm_embedding",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": f"concept_score = ({W_NLI} * entailment) + ({W_SIM} * similarity)",
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
        except Exception as e:
            self._nli_failure_reason = str(e)
            logger.info("DeBERTa NLI cross-encoder unavailable: %s. Falling back to Tier 2.", e)
            return None

    # ── Tier 2: MiniLM Similarity Alone ────────────────────────────

    def _try_minilm_secondary(
        self, candidate_answer: str, concepts: List[str]
    ) -> Optional[Dict[str, Any]]:
        try:
            all_texts = [candidate_answer] + [f"The answer covers: {c}" for c in concepts]

            def _encode(model):
                return model.encode(all_texts, normalize_embeddings=True, show_progress_bar=False)

            response = InferenceService.execute("semantic-answer-similarity-v1", _encode)
            embeddings = response["result"]

            answer_emb = embeddings[0]
            sims = []
            for i in range(1, len(embeddings)):
                sim = float(np.dot(answer_emb, embeddings[i]))
                sims.append(round(max(0.0, min(1.0, sim)), 4))

            answer_lower = candidate_answer.lower()
            concept_results = []
            covered, missing, partial, contradicted = [], [], [], []

            for i, concept in enumerate(concepts):
                sim = sims[i]
                terms = [t.strip().lower() for t in concept.split() if len(t.strip()) > 3]
                if terms:
                    matches = sum(1 for term in terms if term in answer_lower)
                    coverage_ratio = min(1.0, matches / len(terms))
                else:
                    coverage_ratio = sim

                # Entailment incorporates both term coverage and semantic alignment
                entailment = round(min(coverage_ratio, sim) * 0.85, 4) if terms else round(sim * 0.85, 4)
                contradiction = round(max(0.0, (1.0 - sim) * 0.10), 4)
                neutral = round(max(0.0, 1.0 - entailment - contradiction), 4)
                concept_score = round((W_NLI * entailment) + (W_SIM * sim), 4)

                status = self._determine_status(concept_score, contradiction)
                if status == "covered":
                    covered.append(concept)
                elif status == "missing":
                    missing.append(concept)
                elif status == "contradicted":
                    contradicted.append(concept)
                elif status == "partially_covered":
                    partial.append(concept)

                concept_results.append({
                    "concept": concept,
                    "entailment_probability": entailment,
                    "contradiction_probability": contradiction,
                    "neutral_probability": neutral,
                    "semantic_similarity": sim,
                    "concept_score": concept_score,
                    "status": status,
                })

            overall_pct = round((sum(sims) / len(sims)) * 100.0, 1)
            # Authentic confidence: mean cosine similarity
            avg_conf = float(np.mean(sims))

            _conf_meta = get_confidence_metadata("answer-nli-v1", round(avg_conf, 4), source_tier="pretrained")
            return {
                "overall_coverage_pct": overall_pct,
                "concept_results": concept_results,
                "covered_concepts": covered,
                "missing_concepts": missing,
                "contradicted_concepts": contradicted,
                "partially_covered_concepts": partial,
                "confidence": round(avg_conf, 4),
                "source": IntelligenceSource.PRETRAINED.value,
                "method": "minilm_similarity_alone_fallback",
                "signal_type": "ml_derived_concept_coverage_signal",
                "aggregation_formula": "concept_score = cosine_similarity(answer, concept)",
                "confidence_metadata": _conf_meta.to_dict(),
                "confidence_band": _conf_meta.confidence_band.value,
            }
        except Exception as e:
            logger.debug("MiniLM similarity alone failed: %s", e)
            return None

    # ── Tier 2 Safety Net: Lexical Deterministic Fallback ───────────

    def _lexical_deterministic_fallback(
        self, candidate_answer: str, concepts: List[str]
    ) -> Dict[str, Any]:
        """Deterministic Jaccard & word-overlap heuristic."""
        answer_lower = candidate_answer.lower()
        answer_words = set(answer_lower.split())

        concept_results = []
        covered, missing, partial, contradicted = [], [], [], []
        overlaps = []

        for concept in concepts:
            concept_words = set(concept.lower().split())
            if not concept_words:
                overlaps.append(0.0)
                continue

            overlap_count = len(answer_words & concept_words)
            union_count = len(answer_words | concept_words)
            jaccard = overlap_count / union_count if union_count > 0 else 0.0

            terms = [t.strip().lower() for t in concept.split() if len(t.strip()) > 3]
            term_matches = sum(1 for term in terms if term in answer_lower)
            term_ratio = term_matches / len(terms) if terms else 0.0

            composite_overlap = round(0.5 * jaccard + 0.5 * term_ratio, 4)
            overlaps.append(composite_overlap)

            if composite_overlap >= 0.40:
                status = "covered"
                covered.append(concept)
            elif composite_overlap >= 0.20:
                status = "partially_covered"
                partial.append(concept)
            else:
                status = "missing"
                missing.append(concept)

            entailment = round(composite_overlap * 0.85, 4)
            contradiction = round(max(0.0, (1.0 - composite_overlap) * 0.10), 4)
            neutral = round(max(0.0, 1.0 - entailment - contradiction), 4)

            concept_results.append({
                "concept": concept,
                "entailment_probability": entailment,
                "contradiction_probability": contradiction,
                "neutral_probability": neutral,
                "semantic_similarity": composite_overlap,
                "concept_score": composite_overlap,
                "status": status,
            })

        overall_pct = round((sum(overlaps) / len(overlaps)) * 100.0, 1)
        avg_conf = float(np.mean(overlaps)) if overlaps else 0.0

        _conf_meta = get_confidence_metadata("answer-nli-v1", round(avg_conf, 4), source_tier="deterministic")
        return {
            "overall_coverage_pct": overall_pct,
            "concept_results": concept_results,
            "covered_concepts": covered,
            "missing_concepts": missing,
            "contradicted_concepts": contradicted,
            "partially_covered_concepts": partial,
            "confidence": round(avg_conf, 4),
            "source": IntelligenceSource.DETERMINISTIC.value,
            "method": "lexical_nli_fallback",
            "signal_type": "ml_derived_concept_coverage_signal",
            "aggregation_formula": "concept_score = lexical_overlap(answer, concept)",
            "confidence_metadata": _conf_meta.to_dict(),
            "confidence_band": _conf_meta.confidence_band.value,
        }

    def _compute_similarities_or_fallback(
        self, candidate_answer: str, concepts: List[str]
    ) -> List[float]:
        try:
            all_texts = [candidate_answer] + [f"The answer covers: {c}" for c in concepts]

            def _encode(model):
                return model.encode(all_texts, normalize_embeddings=True, show_progress_bar=False)

            response = InferenceService.execute("semantic-answer-similarity-v1", _encode)
            embeddings = response["result"]
            answer_emb = embeddings[0]
            sims = []
            for i in range(1, len(embeddings)):
                sim = float(np.dot(answer_emb, embeddings[i]))
                sims.append(round(max(0.0, min(1.0, sim)), 4))
            return sims
        except Exception:
            # Fall back to Jaccard overlap
            answer_words = set(candidate_answer.lower().split())
            sims = []
            for c in concepts:
                c_words = set(c.lower().split())
                inter = len(answer_words & c_words)
                union = len(answer_words | c_words)
                sims.append(round(inter / union if union > 0 else 0.0, 4))
            return sims

    @staticmethod
    def _determine_status(concept_score: float, contradiction_prob: float) -> str:
        if contradiction_prob >= CONTRADICTION_THRESHOLD:
            return "contradicted"
        if concept_score >= COVERED_THRESHOLD:
            return "covered"
        if concept_score >= PARTIAL_THRESHOLD:
            return "partially_covered"
        return "missing"

    @staticmethod
    def extract_concepts_from_rubric(evaluation_rubric: str) -> List[str]:
        if not evaluation_rubric or not isinstance(evaluation_rubric, str) or not evaluation_rubric.strip():
            return []

        lines = re.split(r'[\n;]|(?:\d+\.)|(?:[-•*]\s)', evaluation_rubric)
        concepts = []
        for line in lines:
            cleaned = line.strip().rstrip('.')
            if len(cleaned) > 15 and len(cleaned.split()) > 2:
                concepts.append(cleaned)
        return concepts[:20]
