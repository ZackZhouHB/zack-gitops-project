"""Model routing for cost optimization"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class ModelRouter:
    """Route queries to appropriate model based on complexity"""
    
    # Model configs: (model_id, cost_per_1k_input, cost_per_1k_output)
    MODELS = {
        "fast": ("anthropic.claude-3-haiku-20240307-v1:0", 0.00025, 0.00125),
        "smart": ("anthropic.claude-3-sonnet-20240229-v1:0", 0.003, 0.015),
    }
    
    # Keywords suggesting complex query
    COMPLEX_INDICATORS = [
        "analyze", "compare", "explain in detail", "step by step",
        "pros and cons", "comprehensive", "thorough", "evaluate",
        "summarize all", "relationship between", "implications"
    ]
    
    # Keywords suggesting simple query
    SIMPLE_INDICATORS = [
        "what is", "who is", "when", "where", "define",
        "list", "name", "how many", "yes or no"
    ]
    
    @classmethod
    def classify_complexity(cls, query: str) -> str:
        """Classify query as 'simple' or 'complex'"""
        query_lower = query.lower()
        
        # Check for complex indicators
        complex_score = sum(1 for ind in cls.COMPLEX_INDICATORS if ind in query_lower)
        simple_score = sum(1 for ind in cls.SIMPLE_INDICATORS if ind in query_lower)
        
        # Length is also an indicator
        if len(query) > 200:
            complex_score += 1
        
        return "complex" if complex_score > simple_score else "simple"
    
    @classmethod
    def route(cls, query: str, force_model: str = None) -> Tuple[str, str]:
        """
        Route query to appropriate model.
        Returns: (model_id, model_tier)
        """
        if force_model and force_model in cls.MODELS:
            return cls.MODELS[force_model][0], force_model
        
        complexity = cls.classify_complexity(query)
        tier = "smart" if complexity == "complex" else "fast"
        model_id = cls.MODELS[tier][0]
        
        logger.info(f"Routed query to {tier} model (complexity: {complexity})")
        return model_id, tier
    
    @classmethod
    def estimate_cost(cls, tier: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a query"""
        if tier not in cls.MODELS:
            tier = "fast"
        _, input_cost, output_cost = cls.MODELS[tier]
        return (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)
