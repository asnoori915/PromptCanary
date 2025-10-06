"""
ML METRICS SERVICE - Real evaluation metrics for prompt quality

This service provides actual ML metrics to evaluate prompt quality:
1. BLEU score - measures how similar generated text is to reference
2. ROUGE score - measures recall and precision of key information
3. Semantic similarity - measures meaning similarity using embeddings
4. Length consistency - measures if output length matches expectations
5. Diversity - measures how varied the outputs are

This replaces the simple heuristic scoring with real ML evaluation.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from app.utils import get_logger, round_score

logger = get_logger(__name__)

class MLMetricsService:
    """Service for computing ML evaluation metrics."""
    
    def __init__(self):
        """Initialize ML metrics service with lazy loading."""
        self._sentence_model = None
        self._rouge_scorer = None
        self._bleu_scorer = None
    
    def _get_sentence_model(self):
        """Lazy load sentence transformer model."""
        if self._sentence_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model")
            except ImportError:
                logger.warning("sentence-transformers not available, semantic similarity disabled")
        return self._sentence_model
    
    def _get_rouge_scorer(self):
        """Lazy load ROUGE scorer."""
        if self._rouge_scorer is None:
            try:
                from rouge_score import rouge_scorer
                self._rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
                logger.info("Loaded ROUGE scorer")
            except ImportError:
                logger.warning("rouge-score not available, ROUGE metrics disabled")
        return self._rouge_scorer
    
    def _get_bleu_scorer(self):
        """Lazy load BLEU scorer."""
        if self._bleu_scorer is None:
            try:
                import nltk
                nltk.download('punkt', quiet=True)
                from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
                self._bleu_scorer = (sentence_bleu, SmoothingFunction())
                logger.info("Loaded BLEU scorer")
            except ImportError:
                logger.warning("nltk not available, BLEU metrics disabled")
        return self._bleu_scorer
    
    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts using embeddings.
        
        Returns similarity score between 0 and 1 (1 = identical meaning).
        """
        model = self._get_sentence_model()
        if model is None:
            return 0.0
        
        try:
            embeddings = model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return round_score(float(similarity))
        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0
    
    def compute_rouge_scores(self, reference: str, candidate: str) -> Dict[str, float]:
        """
        Compute ROUGE scores (recall, precision, F1) for text similarity.
        
        ROUGE measures how much of the reference text is captured in the candidate.
        """
        scorer = self._get_rouge_scorer()
        if scorer is None:
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
        
        try:
            scores = scorer.score(reference, candidate)
            return {
                "rouge1": round_score(scores['rouge1'].fmeasure),
                "rouge2": round_score(scores['rouge2'].fmeasure),
                "rougeL": round_score(scores['rougeL'].fmeasure)
            }
        except Exception as e:
            logger.error(f"Error computing ROUGE scores: {e}")
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    
    def compute_bleu_score(self, reference: str, candidate: str) -> float:
        """
        Compute BLEU score for text similarity.
        
        BLEU measures n-gram overlap between reference and candidate.
        """
        scorer_data = self._get_bleu_scorer()
        if scorer_data is None:
            return 0.0
        
        try:
            sentence_bleu, smoothing = scorer_data
            reference_tokens = reference.lower().split()
            candidate_tokens = candidate.lower().split()
            
            score = sentence_bleu(
                [reference_tokens], 
                candidate_tokens, 
                smoothing_function=smoothing.method1
            )
            return round_score(float(score))
        except Exception as e:
            logger.error(f"Error computing BLEU score: {e}")
            return 0.0
    
    def compute_length_consistency(self, expected_length: int, actual_length: int) -> float:
        """
        Compute how well actual length matches expected length.
        
        Returns score between 0 and 1 (1 = perfect match).
        """
        if expected_length == 0:
            return 1.0
        
        ratio = min(actual_length, expected_length) / max(actual_length, expected_length)
        return round_score(ratio)
    
    def compute_diversity_score(self, responses: List[str]) -> float:
        """
        Compute diversity score for multiple responses.
        
        Measures how different the responses are from each other.
        Higher score = more diverse responses.
        """
        if len(responses) < 2:
            return 0.0
        
        model = self._get_sentence_model()
        if model is None:
            return 0.0
        
        try:
            embeddings = model.encode(responses)
            similarities = []
            
            # Compute pairwise similarities
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )
                    similarities.append(sim)
            
            # Diversity = 1 - average similarity
            avg_similarity = np.mean(similarities) if similarities else 0.0
            diversity = 1.0 - avg_similarity
            return round_score(max(0.0, diversity))
        except Exception as e:
            logger.error(f"Error computing diversity score: {e}")
            return 0.0
    
    def evaluate_response_quality(
        self, 
        prompt: str, 
        response: str, 
        reference_response: Optional[str] = None,
        expected_length: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Comprehensive evaluation of response quality.
        
        This is the main function that combines all metrics to give
        a complete picture of how good a response is.
        """
        metrics = {}
        
        # Basic metrics
        metrics["response_length"] = len(response.split())
        
        # Reference-based metrics (if reference provided)
        if reference_response:
            metrics["bleu_score"] = self.compute_bleu_score(reference_response, response)
            rouge_scores = self.compute_rouge_scores(reference_response, response)
            metrics.update(rouge_scores)
            metrics["semantic_similarity"] = self.compute_semantic_similarity(reference_response, response)
        
        # Length consistency (if expected length provided)
        if expected_length:
            metrics["length_consistency"] = self.compute_length_consistency(
                expected_length, metrics["response_length"]
            )
        
        # Overall quality score (weighted combination)
        quality_factors = []
        if "bleu_score" in metrics:
            quality_factors.append(metrics["bleu_score"] * 0.3)
        if "rouge1" in metrics:
            quality_factors.append(metrics["rouge1"] * 0.3)
        if "semantic_similarity" in metrics:
            quality_factors.append(metrics["semantic_similarity"] * 0.4)
        
        if quality_factors:
            metrics["overall_quality"] = round_score(sum(quality_factors))
        else:
            # Fallback to simple length-based scoring
            metrics["overall_quality"] = round_score(
                min(1.0, metrics["response_length"] / 50.0)
            )
        
        return metrics

# Global instance
ml_metrics = MLMetricsService()
