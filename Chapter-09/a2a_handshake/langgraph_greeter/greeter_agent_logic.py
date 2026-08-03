"""Minimal LangGraph workflow for the Chapter 9 Greeter."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class GreeterState(TypedDict, total=False):
    message: str


def greet(state: GreeterState) -> GreeterState:
    return {"message": "Hello from your new friend, the LangGraph agent!"}


workflow = StateGraph(GreeterState)
workflow.add_node("greet", greet)
workflow.add_edge(START, "greet")
workflow.add_edge("greet", END)
langgraph_app = workflow.compile()
