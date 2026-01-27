"""Simple RAG evaluation metrics"""
import logging
from typing import List, Dict
import json

logger = logging.getLogger(__name__)

class RAGEvaluator:
    """Evaluate RAG response quality"""
    
    def __init__(self, bedrock_client, model_id: str):
        self.bedrock = bedrock_client
        self.model_id = model_id
    
    def evaluate(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """
        Evaluate RAG response on key metrics.
        Returns scores 0-1 for each metric.
        """
        context_str = "\n---\n".join(contexts[:3])
        
        prompt = f"""Evaluate this RAG response. Score each metric 0-10.

Question: {question}

Retrieved Context:
{context_str}

Generated Answer: {answer}

Rate these metrics (0-10):
1. Faithfulness: Is the answer grounded in the context? (not hallucinated)
2. Relevance: Does the answer address the question?
3. Completeness: Does the answer fully address the question?

Return JSON only: {{"faithfulness": X, "relevance": X, "completeness": X, "reasoning": "brief explanation"}}"""

        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0
            })
            
            response = self.bedrock.invoke_model(modelId=self.model_id, body=body)
            result = json.loads(response["body"].read())["content"][0]["text"]
            
            # Parse JSON from response
            scores = json.loads(result)
            return {
                "faithfulness": scores.get("faithfulness", 0) / 10,
                "relevance": scores.get("relevance", 0) / 10,
                "completeness": scores.get("completeness", 0) / 10,
                "reasoning": scores.get("reasoning", ""),
                "overall": (scores.get("faithfulness", 0) + scores.get("relevance", 0) + scores.get("completeness", 0)) / 30
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}
    
    def batch_evaluate(self, test_cases: List[Dict]) -> Dict:
        """Evaluate multiple test cases and return aggregate scores"""
        results = []
        for case in test_cases:
            score = self.evaluate(case["question"], case["answer"], case.get("contexts", []))
            results.append(score)
        
        # Aggregate
        valid = [r for r in results if "error" not in r]
        if not valid:
            return {"error": "All evaluations failed"}
        
        return {
            "num_cases": len(test_cases),
            "avg_faithfulness": sum(r["faithfulness"] for r in valid) / len(valid),
            "avg_relevance": sum(r["relevance"] for r in valid) / len(valid),
            "avg_completeness": sum(r["completeness"] for r in valid) / len(valid),
            "avg_overall": sum(r["overall"] for r in valid) / len(valid),
        }
