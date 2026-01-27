"""LangGraph agent with tools for multi-step reasoning"""
import json
import logging
from typing import TypedDict, List, Annotated
import operator

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State passed between agent nodes"""
    query: str
    context: Annotated[List[str], operator.add]  # Accumulates context
    tools_used: Annotated[List[str], operator.add]
    thoughts: Annotated[List[str], operator.add]
    answer: str

class RAGAgent:
    """Simple ReAct-style agent using LangGraph pattern"""
    
    def __init__(self, rag_service, bedrock_client, model_id: str):
        self.rag = rag_service
        self.bedrock = bedrock_client
        self.model_id = model_id
        self.tools = {
            "search_docs": self._search_docs,
            "summarize": self._summarize,
        }
    
    async def run(self, query: str, user_groups: List[str] = None) -> dict:
        """Run agent with ReAct loop"""
        state = AgentState(
            query=query,
            context=[],
            tools_used=[],
            thoughts=[],
            answer=""
        )
        
        # Step 1: Plan
        plan = self._plan(query)
        state["thoughts"].append(f"Plan: {plan}")
        
        # Step 2: Execute tools based on plan
        if "search" in plan.lower():
            docs = await self._search_docs(query, user_groups)
            state["context"].extend([d["content"] for d in docs])
            state["tools_used"].append("search_docs")
            state["thoughts"].append(f"Found {len(docs)} relevant documents")
        
        # Step 3: Generate answer
        if state["context"]:
            state["answer"] = self._generate_answer(query, state["context"])
            state["tools_used"].append("answer")
        else:
            state["answer"] = "I couldn't find relevant information to answer your question."
        
        return {
            "answer": state["answer"],
            "tools_used": state["tools_used"],
            "thoughts": state["thoughts"],
            "sources_count": len(state["context"])
        }
    
    def _plan(self, query: str) -> str:
        """Decide what tools to use"""
        prompt = f"""Given this query, what should I do?
Query: {query}

Available tools:
- search_docs: Search knowledge base
- summarize: Summarize long content
- answer: Generate final answer

Respond with a brief plan (1-2 sentences):"""
        
        return self._call_llm(prompt)
    
    async def _search_docs(self, query: str, user_groups: List[str] = None) -> List[dict]:
        """Search RAG knowledge base"""
        result = await self.rag.query(
            query, 
            top_k=5, 
            use_rerank=True,
            user_groups=user_groups
        )
        # Return answer as context since sources don't have full content
        return [{"content": result.get("answer", "")}]
    
    def _summarize(self, text: str) -> str:
        """Summarize long content"""
        prompt = f"Summarize this concisely:\n\n{text[:3000]}"
        return self._call_llm(prompt)
    
    def _generate_answer(self, query: str, context: List[str]) -> str:
        """Generate final answer from context"""
        ctx = "\n\n".join(context[:5])
        prompt = f"""Based on this context, answer the question.

Context:
{ctx}

Question: {query}

Answer:"""
        return self._call_llm(prompt)
    
    def _call_llm(self, prompt: str) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1
        })
        
        response = self.bedrock.invoke_model(modelId=self.model_id, body=body)
        return json.loads(response["body"].read())["content"][0]["text"]
