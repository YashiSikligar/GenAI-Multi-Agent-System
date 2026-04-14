# router_agent.py
from typing import TypedDict, Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END


#state

class AgentState(TypedDict):
    query: str
    route: Literal["sql", "rag", "unknown"]
    answer: str


#nodes
def make_router_node(llm: ChatOpenAI):
    def router_node(state: AgentState) -> AgentState:
        query = state["query"]
        prompt = f"""You are a query router for a customer support system.
Classify the following query as either:
- "sql" - if it asks about customers, tickets, accounts, billing records, support tickets, 
           user counts, subscription plans, issue statuses, or any structured data
- "rag" - if it asks about policies, procedures, guidelines, terms of service, 
           refund policy, privacy policy, SLA, or any document/knowledge-base content

Respond with ONLY one word: sql OR rag

Query: {query}
Classification:"""
        result = llm.invoke(prompt)
        route = result.content.strip().lower()
        if route not in ("sql", "rag"):
            route = "rag"  # default fallback
        return {**state, "route": route}
    return router_node


def make_sql_node(sql_agent):
    def sql_node(state: AgentState) -> AgentState:
        answer = sql_agent.query(state["query"])
        return {**state, "answer": answer}
    return sql_node


def make_rag_node(rag_agent):
    def rag_node(state: AgentState) -> AgentState:
        answer = rag_agent.query(state["query"])
        return {**state, "answer": answer}
    return rag_node


def route_decision(state: AgentState) -> str:
    return state["route"]


# here we are creating the graph

class RouterOrchestrator:
    def __init__(self, sql_agent, rag_agent):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.sql_agent = sql_agent
        self.rag_agent = rag_agent
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("router",    make_router_node(self.llm))
        builder.add_node("sql_agent", make_sql_node(self.sql_agent))
        builder.add_node("rag_agent", make_rag_node(self.rag_agent))

        builder.set_entry_point("router")
        builder.add_conditional_edges(
            "router",
            route_decision,
            {
                "sql": "sql_agent",
                "rag": "rag_agent",
            },
        )
        builder.add_edge("sql_agent", END)
        builder.add_edge("rag_agent", END)

        return builder.compile()

    def run(self, query: str) -> dict:
        
        initial_state: AgentState = {"query": query, "route": "unknown", "answer": ""}
        final_state = self.graph.invoke(initial_state)
        return {
            "answer": final_state["answer"],
            "route":  final_state["route"],
        }