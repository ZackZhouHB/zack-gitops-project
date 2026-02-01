"""RAG Evaluation Metrics - RAGAS-style implementation"""
import json
import logging
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    faithfulness: float      # Is answer grounded in context?
    relevance: float         # Does answer address question?
    context_precision: float # Are retrieved docs relevant?
    reasoning: str
    
    @property
    def overall(self) -> float:
        return (self.faithfulness + self.relevance + self.context_precision) / 3

@dataclass 
class BatchResult:
    num_cases: int
    avg_faithfulness: float
    avg_relevance: float
    avg_context_precision: float
    avg_overall: float
    results: List[Dict]


class RAGEvaluator:
    """
    Evaluates RAG quality using LLM-as-judge.
    Supports vLLM (local) or Bedrock (cloud).
    """
    
    def __init__(self, vllm_url: str = None, bedrock_client = None, backend: str = "vllm"):
        self.vllm_url = vllm_url or "http://llm-server:8000"
        self.bedrock = bedrock_client
        self.backend = backend
    
    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate a single RAG response"""
        
        context_str = "\n---\n".join(contexts[:5])  # Limit context
        
        prompt = f"""You are evaluating a RAG (Retrieval-Augmented Generation) system.

QUESTION: {question}

RETRIEVED CONTEXT:
{context_str}

GENERATED ANSWER: {answer}

Rate these metrics from 0-10:

1. FAITHFULNESS: Is the answer factually grounded in the retrieved context? 
   - 10 = Every claim is supported by context
   - 0 = Answer contains hallucinations not in context

2. RELEVANCE: Does the answer actually address the question?
   - 10 = Directly and completely answers the question
   - 0 = Answer is off-topic or doesn't address the question

3. CONTEXT_PRECISION: Are the retrieved documents relevant to the question?
   - 10 = All retrieved docs are highly relevant
   - 0 = Retrieved docs are unrelated to the question

Return ONLY valid JSON:
{{"faithfulness": <0-10>, "relevance": <0-10>, "context_precision": <0-10>, "reasoning": "<brief explanation>"}}"""

        try:
            response = self._call_llm(prompt)
            scores = json.loads(response)
            
            return EvaluationResult(
                faithfulness=scores.get("faithfulness", 0) / 10,
                relevance=scores.get("relevance", 0) / 10,
                context_precision=scores.get("context_precision", 0) / 10,
                reasoning=scores.get("reasoning", "")
            )
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return EvaluationResult(0, 0, 0, f"Error: {e}")
    
    def evaluate_batch(self, test_cases: List[Dict]) -> BatchResult:
        """
        Evaluate multiple test cases.
        Each case: {"question": str, "answer": str, "contexts": List[str]}
        """
        results = []
        for case in test_cases:
            result = self.evaluate(
                case["question"],
                case["answer"],
                case.get("contexts", [])
            )
            results.append({
                "question": case["question"],
                **asdict(result)
            })
        
        valid = [r for r in results if r["faithfulness"] > 0]
        if not valid:
            return BatchResult(len(test_cases), 0, 0, 0, 0, results)
        
        return BatchResult(
            num_cases=len(test_cases),
            avg_faithfulness=sum(r["faithfulness"] for r in valid) / len(valid),
            avg_relevance=sum(r["relevance"] for r in valid) / len(valid),
            avg_context_precision=sum(r["context_precision"] for r in valid) / len(valid),
            avg_overall=sum((r["faithfulness"] + r["relevance"] + r["context_precision"]) / 3 for r in valid) / len(valid),
            results=results
        )
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM backend"""
        if self.backend == "vllm":
            return self._call_vllm(prompt)
        else:
            return self._call_bedrock(prompt)
    
    def _call_vllm(self, prompt: str) -> str:
        resp = httpx.post(
            f"{self.vllm_url}/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-3B-Instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0
            },
            timeout=60.0
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    
    def _call_bedrock(self, prompt: str) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0
        })
        response = self.bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        return json.loads(response["body"].read())["content"][0]["text"]
