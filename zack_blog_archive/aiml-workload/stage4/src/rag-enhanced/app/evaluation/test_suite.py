"""Test Suite Builder - Generate Q&A pairs from documents"""
import json
import logging
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    question: str
    expected_keywords: List[str]  # Keywords that should appear in answer
    source_hint: Optional[str] = None  # Which doc should be retrieved
    
    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "expected_keywords": self.expected_keywords,
            "source_hint": self.source_hint
        }


class TestSuiteBuilder:
    """Generate test cases from documents using LLM"""
    
    def __init__(self, vllm_url: str = None):
        self.vllm_url = vllm_url or "http://llm-server:8000"
    
    def generate_from_text(
        self,
        content: str,
        source: str,
        num_questions: int = 5
    ) -> List[TestCase]:
        """Generate Q&A test cases from document content"""
        
        # Truncate content if too long
        content = content[:4000]
        
        prompt = f"""Generate {num_questions} question-answer pairs from this document.
For each question, provide keywords that MUST appear in a correct answer.

DOCUMENT SOURCE: {source}
DOCUMENT CONTENT:
{content}

Return ONLY valid JSON array:
[
  {{"question": "...", "keywords": ["keyword1", "keyword2"]}},
  ...
]"""

        try:
            resp = httpx.post(
                f"{self.vllm_url}/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-3B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                timeout=120.0
            )
            resp.raise_for_status()
            response = resp.json()["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            qa_pairs = json.loads(response)
            
            return [
                TestCase(
                    question=qa["question"],
                    expected_keywords=qa.get("keywords", []),
                    source_hint=source
                )
                for qa in qa_pairs
            ]
        except Exception as e:
            logger.error(f"Failed to generate test cases: {e}")
            return []
    
    def generate_from_documents(
        self,
        documents: List[Dict],  # [{"content": str, "source": str}]
        questions_per_doc: int = 3
    ) -> List[TestCase]:
        """Generate test cases from multiple documents"""
        all_cases = []
        for doc in documents:
            cases = self.generate_from_text(
                doc["content"],
                doc["source"],
                questions_per_doc
            )
            all_cases.extend(cases)
        return all_cases


# Predefined test cases for common scenarios
BASELINE_TEST_CASES = [
    TestCase(
        question="What is Kubernetes?",
        expected_keywords=["container", "orchestration", "deployment"],
        source_hint=None
    ),
    TestCase(
        question="What are Pods in Kubernetes?",
        expected_keywords=["smallest", "deployable", "container"],
        source_hint=None
    ),
    TestCase(
        question="How does Kubernetes handle scaling?",
        expected_keywords=["replicas", "horizontal", "auto"],
        source_hint=None
    ),
]
