"""LangGraph agent with tools for multi-step reasoning"""
import json
import logging
import re
from datetime import datetime
from typing import TypedDict, List, Annotated
import operator

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State passed between agent nodes"""
    query: str
    context: Annotated[List[str], operator.add]
    tools_used: Annotated[List[str], operator.add]
    thoughts: Annotated[List[str], operator.add]
    answer: str

class RAGAgent:
    """ReAct-style agent with multiple tools"""
    
    def __init__(self, rag_service, bedrock_client, model_id: str):
        self.rag = rag_service
        self.bedrock = bedrock_client
        self.model_id = model_id
        self.tools = {
            "search_docs": "Search knowledge base for relevant documents",
            "list_sources": "List all available document sources",
            "calculate": "Perform mathematical calculations",
            "get_date": "Get current date and time",
            "compare_docs": "Compare information across multiple documents",
        }
    
    async def run(self, query: str, user_groups: List[str] = None) -> dict:
        """Run agent with ReAct loop"""
        state = AgentState(
            query=query, context=[], tools_used=[], thoughts=[], answer=""
        )
        
        # Step 1: Plan - decide which tools to use
        plan = self._plan(query)
        state["thoughts"].append(f"Plan: {plan}")
        
        # Step 2: Execute tools based on plan
        tools_to_use = self._parse_tools_from_plan(plan)
        
        for tool in tools_to_use:
            if tool == "search_docs":
                docs = await self._search_docs(query, user_groups)
                state["context"].extend(docs)
                state["tools_used"].append("search_docs")
                state["thoughts"].append(f"Found {len(docs)} relevant chunks")
            
            elif tool == "list_sources":
                sources = await self._list_sources(user_groups)
                state["context"].append(f"Available sources: {sources}")
                state["tools_used"].append("list_sources")
                state["thoughts"].append(f"Listed {len(sources.split(','))} sources")
            
            elif tool == "calculate":
                calc_result = self._calculate(query)
                if calc_result:
                    state["context"].append(f"Calculation result: {calc_result}")
                    state["tools_used"].append("calculate")
                    state["thoughts"].append(f"Calculated: {calc_result}")
            
            elif tool == "get_date":
                date_info = self._get_date()
                state["context"].append(date_info)
                state["tools_used"].append("get_date")
                state["thoughts"].append("Got current date/time")
            
            elif tool == "compare_docs":
                comparison = await self._compare_docs(query, user_groups)
                state["context"].append(comparison)
                state["tools_used"].append("compare_docs")
                state["thoughts"].append("Compared documents")
        
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
        """Decide what tools to use - rule-based for reliability"""
        query_lower = query.lower()
        tools = []
        
        # Date/time queries
        if any(w in query_lower for w in ["today", "date", "time", "now", "current"]):
            tools.append("get_date")
        
        # Math queries  
        if any(w in query_lower for w in ["calculate", "what is", "how much"]) and \
           re.search(r'\d+\s*[+\-*/]\s*\d+', query):
            tools.append("calculate")
        
        # List queries
        if any(w in query_lower for w in ["list", "all documents", "all sources", "what documents"]):
            tools.append("list_sources")
        
        # Compare queries
        if any(w in query_lower for w in ["compare", "difference", "versus", "vs"]):
            tools.append("compare_docs")
        
        # Default to search for knowledge queries
        if not tools or any(w in query_lower for w in ["what", "how", "why", "explain", "tell me", "about"]):
            if "search_docs" not in tools:
                tools.append("search_docs")
        
        return f"Using tools: {', '.join(tools)}"
    
    def _parse_tools_from_plan(self, plan: str) -> List[str]:
        """Extract tool names from plan"""
        tools = []
        plan_lower = plan.lower()
        for tool in self.tools.keys():
            if tool in plan_lower:
                tools.append(tool)
        return tools if tools else ["search_docs"]  # Default to search
    
    async def _search_docs(self, query: str, user_groups: List[str] = None) -> List[str]:
        """Search RAG knowledge base"""
        result = await self.rag.query(query, top_k=5, use_rerank=True, user_groups=user_groups)
        return [result.get("answer", "")]
    
    async def _list_sources(self, user_groups: List[str] = None) -> str:
        """List available document sources"""
        try:
            docs = await self.rag.list_documents(user_groups=user_groups)
            sources = [d.get("source", "unknown") for d in docs.get("documents", [])]
            return ", ".join(sources) if sources else "No documents found"
        except:
            return "Unable to list sources"
    
    def _calculate(self, query: str) -> str:
        """Extract and calculate math expressions"""
        # Find numbers and operators in query
        match = re.search(r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)', query)
        if match:
            try:
                a, op, b = float(match.group(1)), match.group(2), float(match.group(3))
                result = {'+': a+b, '-': a-b, '*': a*b, '/': a/b if b else 0}[op]
                return f"{a} {op} {b} = {result}"
            except:
                pass
        return None
    
    def _get_date(self) -> str:
        """Get current date and time"""
        now = datetime.now()
        return f"Current date: {now.strftime('%Y-%m-%d')}, Time: {now.strftime('%H:%M:%S')}, Day: {now.strftime('%A')}"
    
    async def _compare_docs(self, query: str, user_groups: List[str] = None) -> str:
        """Compare information across documents"""
        result = await self.rag.query(
            f"Compare and contrast: {query}", 
            top_k=10, use_rerank=True, user_groups=user_groups
        )
        return result.get("answer", "")
    
    def _generate_answer(self, query: str, context: List[str]) -> str:
        """Generate final answer from context"""
        ctx = "\n\n".join(context[:5])
        prompt = f"""Based on this context, answer the question comprehensively.

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
