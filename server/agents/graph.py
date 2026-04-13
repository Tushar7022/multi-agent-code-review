from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.security_agent import security_agent
from agents.performance_agent import performance_agent
from agents.maintainability_agent import maintainability_agent
from agents.synthesizer_agent import synthesizer_agent


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # register all nodes
    graph.add_node("security",        security_agent)
    graph.add_node("performance",     performance_agent)
    graph.add_node("maintainability", maintainability_agent)
    graph.add_node("synthesizer",     synthesizer_agent)

    # START fans out to all 3 specialist agents in parallel
    graph.add_edge(START, "security")
    graph.add_edge(START, "performance")
    graph.add_edge(START, "maintainability")

    # all 3 specialist agents feed into synthesizer
    graph.add_edge("security",        "synthesizer")
    graph.add_edge("performance",     "synthesizer")
    graph.add_edge("maintainability", "synthesizer")

    # synthesizer is the final node
    graph.add_edge("synthesizer", END)

    return graph


# compiled graph — this is what main.py imports and calls
review_graph = build_graph().compile()