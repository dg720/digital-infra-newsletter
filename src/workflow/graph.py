"""LangGraph workflow definition."""

from typing import Dict, Any, TypedDict, Annotated, List
import operator

from langgraph.graph import StateGraph, END

from .nodes import (
    manager_init_node,
    research_data_centers_node,
    research_connectivity_fibre_node,
    research_towers_wireless_node,
    review_sections_node,
    route_fix_plans_node,
    editor_pass_node,
    assemble_newsletter_node,
    persist_artifacts_node,
)
from ..schemas.state import NewsletterState

# Reducer for dict merging
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**a, **b}

class WorkflowState(TypedDict, total=False):
    """State type for the newsletter workflow."""
    # Input
    prompt: str
    max_review_rounds: int
    active_players: Dict[str, List[str]]
    verticals: List[str]
    
    # Parsed state
    newsletter_state: Dict[str, Any]
    
    # Research outputs
    evidence_packs: Annotated[Dict[str, Any], merge_dicts]
    drafts: Annotated[Dict[str, Any], merge_dicts]
    
    # Review outputs
    current_review_round: int
    reviews: Annotated[Dict[str, List[Any]], merge_dicts]
    sections_to_fix: List[str]
    
    # Editor outputs
    editor_changes: List[str]
    
    # Final outputs
    newsletter_md: str
    output_paths: Dict[str, Any]


def create_newsletter_graph() -> StateGraph:
    """
    Create the LangGraph workflow for newsletter generation.
    
    Graph structure:
    1. manager_init -> parallel research nodes
    2. research nodes -> review_sections
    3. review_sections -> route_fix_plans
    4. route_fix_plans -> either back to research or editor_pass
    5. editor_pass -> assemble_newsletter
    6. assemble_newsletter -> persist_artifacts -> END
    """
    
    # Create graph with state schema
    graph = StateGraph(WorkflowState)
    
    # Add nodes
    graph.add_node("manager_init", manager_init_node)
    graph.add_node("research_data_centers", research_data_centers_node)
    graph.add_node("research_connectivity_fibre", research_connectivity_fibre_node)
    graph.add_node("research_towers_wireless", research_towers_wireless_node)
    graph.add_node("review_sections", review_sections_node)
    graph.add_node("editor_pass", editor_pass_node)
    graph.add_node("assemble_newsletter", assemble_newsletter_node)
    graph.add_node("persist_artifacts", persist_artifacts_node)
    
    # Set entry point
    graph.set_entry_point("manager_init")
    
    # Add edges from manager to research (will be parallel in execution)
    graph.add_edge("manager_init", "research_data_centers")
    graph.add_edge("manager_init", "research_connectivity_fibre")
    graph.add_edge("manager_init", "research_towers_wireless")
    
    # Research nodes converge to review
    graph.add_edge("research_data_centers", "review_sections")
    graph.add_edge("research_connectivity_fibre", "review_sections")
    graph.add_edge("research_towers_wireless", "review_sections")
    
    # Conditional routing after review
    graph.add_conditional_edges(
        "review_sections",
        route_fix_plans_node,
        {
            "editor_pass": "editor_pass",
            "research_fixes": "research_data_centers",  # Simplified - revisit all
        }
    )
    
    # Editor to assembly to persistence
    graph.add_edge("editor_pass", "assemble_newsletter")
    graph.add_edge("assemble_newsletter", "persist_artifacts")
    graph.add_edge("persist_artifacts", END)
    
    return graph


async def run_newsletter_generation(
    prompt: str,
    max_review_rounds: int = 2,
    active_players: dict | None = None,
    verticals: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Run the full newsletter generation workflow.
    
    Args:
        prompt: Natural language description of desired newsletter.
        max_review_rounds: Maximum review iterations.
    
    Returns:
        Final workflow state with output paths.
    """
    # Create and compile graph
    graph = create_newsletter_graph()
    compiled = graph.compile()
    
    # Initial state
    initial_state: WorkflowState = {
        "prompt": prompt,
        "max_review_rounds": max_review_rounds,
    }
    if active_players:
        initial_state["active_players"] = active_players
    if verticals:
        initial_state["verticals"] = verticals
    
    # Run workflow
    final_state = await compiled.ainvoke(initial_state)
    
    return final_state


async def run_newsletter_generation_streaming(
    prompt: str,
    max_review_rounds: int = 2,
    active_players: dict = None,
    verticals: list[str] | None = None,
):
    """
    Run the newsletter generation workflow with streaming progress updates.
    
    Yields dict events with format:
        {"type": "status", "step": str, "message": str}
        {"type": "debug", "category": str, "content": str, "metadata": dict}
        {"type": "complete", "newsletter_id": str, "paths": dict}
        {"type": "error", "message": str}
    """
    from typing import AsyncGenerator
    import time
    
    # Map node names to user-friendly step names and messages
    node_display = {
        "manager_init": ("manager", "Parsing your request..."),
        "research_data_centers": ("research_data_centers", "Researching Data Centers..."),
        "research_connectivity_fibre": ("research_connectivity", "Researching Connectivity & Fibre..."),
        "research_towers_wireless": ("research_towers", "Researching Towers & Wireless..."),
        "review_sections": ("review", "Reviewing all sections..."),
        "editor_pass": ("editor", "Editor finalizing content..."),
        "assemble_newsletter": ("assemble", "Assembling newsletter..."),
        "persist_artifacts": ("persist", "Saving artifacts..."),
    }
    
    # Create and compile graph
    graph = create_newsletter_graph()
    compiled = graph.compile()
    
    # Initial state - include active_players if provided
    initial_state: WorkflowState = {
        "prompt": prompt,
        "max_review_rounds": max_review_rounds,
    }
    if active_players:
        initial_state["active_players"] = active_players
    if verticals:
        initial_state["verticals"] = verticals
    
    final_state = None
    seen_nodes = set()
    completed_nodes = set()
    
    try:
        # Use astream_events to get real-time updates
        async for event in compiled.astream_events(initial_state, version="v2"):
            event_kind = event.get("event", "")
            event_name = event.get("name", "")
            
            # Track node starts for progress updates
            if event_kind == "on_chain_start":
                if event_name in node_display and event_name not in seen_nodes:
                    seen_nodes.add(event_name)
                    step, message = node_display[event_name]
                    yield {"type": "status", "step": step, "message": message, "status": "start"}
                    yield {
                        "type": "debug",
                        "category": "node",
                        "content": f"▶ Starting: {event_name}",
                        "metadata": {"node": event_name, "action": "start"}
                    }
            
            # Track node completions
            if event_kind == "on_chain_end":
                if event_name in node_display and event_name not in completed_nodes:
                    completed_nodes.add(event_name)
                    step, message = node_display[event_name]
                    yield {"type": "status", "step": step, "message": f"Completed: {message}", "status": "complete"}
                    yield {
                        "type": "debug",
                        "category": "node",
                        "content": f"✓ Completed: {event_name}",
                        "metadata": {"node": event_name, "action": "complete"}
                    }
                    
                if event_name == "LangGraph":
                    # This is the final output
                    final_state = event.get("data", {}).get("output", {})
            
            # Capture tool calls - these show web searches and article fetches
            if event_kind == "on_tool_start":
                tool_name = event_name
                tool_input = event.get("data", {}).get("input", {})
                # Truncate long inputs for display
                input_preview = str(tool_input)[:200] + "..." if len(str(tool_input)) > 200 else str(tool_input)
                yield {
                    "type": "debug",
                    "category": "tool",
                    "content": f"🔧 Tool: {tool_name}",
                    "metadata": {"tool": tool_name, "input": input_preview, "action": "start"}
                }
            
            if event_kind == "on_tool_end":
                tool_name = event_name
                tool_output = event.get("data", {}).get("output", "")
                # Truncate long outputs
                output_preview = str(tool_output)[:300] + "..." if len(str(tool_output)) > 300 else str(tool_output)
                yield {
                    "type": "debug",
                    "category": "tool",
                    "content": f"   └─ Result: {output_preview[:100]}...",
                    "metadata": {"tool": tool_name, "output": output_preview, "action": "end"}
                }
            
            # Capture LLM interactions
            if event_kind == "on_chat_model_start":
                model_name = event_name
                yield {
                    "type": "debug",
                    "category": "llm",
                    "content": f"🤖 LLM: {model_name} processing...",
                    "metadata": {"model": model_name, "action": "start"}
                }
            
            # NOTE: on_chat_model_stream disabled - too verbose, causes character-by-character display
            # if event_kind == "on_chat_model_stream":
            #     chunk = event.get("data", {}).get("chunk", {})
            #     content = getattr(chunk, "content", "") if hasattr(chunk, "content") else ""
            #     if content and len(content) > 0:
            #         yield {
            #             "type": "debug",
            #             "category": "llm_stream",
            #             "content": content,
            #             "metadata": {"action": "stream"}
            #         }
            
            if event_kind == "on_chat_model_end":
                model_name = event_name
                output = event.get("data", {}).get("output", {})
                content = ""
                if hasattr(output, "content"):
                    content = output.content[:200] + "..." if len(output.content) > 200 else output.content
                yield {
                    "type": "debug",
                    "category": "llm",
                    "content": f"   └─ Response: {content[:100]}..." if content else "   └─ Response received",
                    "metadata": {"model": model_name, "action": "end"}
                }
        
        # Extract results and send completion
        if final_state:
            newsletter_state = final_state.get("newsletter_state", {})
            newsletter_id = newsletter_state.get("run_id", "unknown")
            output_paths = final_state.get("output_paths", {})
            
            yield {
                "type": "complete",
                "newsletter_id": newsletter_id,
                "paths": {
                    "newsletter_md": output_paths.get("newsletter_md", ""),
                    "meta": output_paths.get("meta", ""),
                },
            }
        else:
            yield {"type": "error", "message": "No output from workflow"}
            
    except Exception as e:
        yield {"type": "error", "message": str(e)}

