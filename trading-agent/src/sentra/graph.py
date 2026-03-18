from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from sentra.nodes.analyst import analyst_node
from sentra.nodes.blocked import blocked_node
from sentra.nodes.data_fetch import data_fetch_node
from sentra.nodes.human_review import human_review_node
from sentra.nodes.planner import planner_node
from sentra.nodes.recommend import recommend_node
from sentra.nodes.risk_officer import risk_officer_node
from sentra.nodes.strategist import strategist_node
from sentra.state import TradingState


def analyst_router(state: TradingState) -> str:
    if state["analysis"]["needs_replan"] and state.get("replan_count", 0) < 1:
        return "replan"
    return "strategize"


def risk_router(state: TradingState) -> str:
    if state["requires_human_review"]:
        return "human_review"
    return "recommend"


def approval_router(state: TradingState) -> str:
    if state["approval"] == "approved":
        return "recommend"
    return "blocked"


def build_app(checkpointer: InMemorySaver | None = None):
    graph = StateGraph(TradingState)

    graph.add_node("planner", planner_node)
    graph.add_node("data_fetch", data_fetch_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("risk_officer", risk_officer_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("blocked", blocked_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "data_fetch")
    graph.add_edge("data_fetch", "analyst")
    graph.add_conditional_edges(
        "analyst",
        analyst_router,
        {
            "replan": "planner",
            "strategize": "strategist",
        },
    )
    graph.add_edge("strategist", "risk_officer")
    graph.add_conditional_edges(
        "risk_officer",
        risk_router,
        {
            "human_review": "human_review",
            "recommend": "recommend",
        },
    )
    graph.add_conditional_edges(
        "human_review",
        approval_router,
        {
            "recommend": "recommend",
            "blocked": "blocked",
        },
    )
    graph.add_edge("recommend", END)
    graph.add_edge("blocked", END)

    return graph.compile(checkpointer=checkpointer or InMemorySaver())
