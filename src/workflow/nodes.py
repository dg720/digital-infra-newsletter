"""LangGraph node implementations."""

from typing import Dict, Any, List
import asyncio

from ..schemas.state import NewsletterState
from ..schemas.evidence import EvidencePack
from ..schemas.sections import SectionDraft, ReviewResult
from ..constants import Vertical, VERTICAL_DISPLAY_NAMES
from ..agents.manager import parse_natural_language_input, create_initial_state
from ..agents.research import research_vertical
from ..agents.reviewer import review_section
from ..agents.editor import edit_sections
from ..storage.artifacts import ArtifactStore


async def manager_init_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Manager initialization node.
    
    Parses natural language input and initializes the workflow state.
    """
    prompt = state.get("prompt", "")
    max_review_rounds = state.get("max_review_rounds", 2)
    active_players = state.get("active_players", None)
    
    # Parse input
    parsed_input = parse_natural_language_input(prompt)
    
    # Create initial state
    newsletter_state = create_initial_state(prompt, parsed_input, max_review_rounds)
    
    # If active_players provided, override comps
    if active_players:
        newsletter_state.comps = active_players
    
    return {"newsletter_state": newsletter_state.model_dump()}


async def research_node(state: Dict[str, Any], vertical: Vertical) -> Dict[str, Any]:
    """
    Research node for a specific vertical.
    
    Gathers evidence and drafts a section.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    
    # Research the vertical
    evidence_pack, draft = await research_vertical(vertical, newsletter_state)
    
    # Update state
    section_id = vertical.value
    return {
        "evidence_packs": {section_id: evidence_pack.model_dump()},
        "drafts": {section_id: draft.model_dump()},
    }


async def research_data_centers_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Research node for data centers vertical."""
    return await research_node(state, Vertical.DATA_CENTERS)


async def research_connectivity_fibre_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Research node for connectivity & fibre vertical."""
    return await research_node(state, Vertical.CONNECTIVITY_FIBRE)


async def research_towers_wireless_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Research node for towers & wireless vertical."""
    return await research_node(state, Vertical.TOWERS_WIRELESS)


async def review_sections_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Review all section drafts.
    
    Scores each section and produces fix plans if needed.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    current_round = state.get("current_review_round", 0) + 1
    
    # Results containers
    reviews = state.get("reviews", {}).copy()
    sections_to_fix = []
    
    drafts = state.get("drafts", {})
    evidence_packs = state.get("evidence_packs", {})
    
    for section_id, draft_data in drafts.items():
        draft = SectionDraft(**draft_data)
        evidence_pack = EvidencePack(**evidence_packs.get(section_id, {"section_id": section_id}))
        
        # Review the section
        review_result = await review_section(
            draft=draft,
            evidence_pack=evidence_pack,
            state=newsletter_state,
            review_round=current_round,
        )
        
        # Store review result
        if section_id not in reviews:
            reviews[section_id] = []
        reviews[section_id].append(review_result.model_dump())
        
        # Track sections needing fixes
        if not review_result.accepted:
            sections_to_fix.append(section_id)
    
    return {
        "current_review_round": current_round,
        "reviews": reviews,
        "sections_to_fix": sections_to_fix,
    }


def route_fix_plans_node(state: Dict[str, Any]) -> str:
    """
    Route to appropriate next step based on review results.
    
    Returns the name of the next node to execute.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    current_round = state.get("current_review_round", 0)
    sections_to_fix = state.get("sections_to_fix", [])
    
    # Check if all sections passed or max rounds reached
    if not sections_to_fix or current_round >= newsletter_state.max_review_rounds:
        return "editor_pass"
    
    # More fixes needed
    return "research_fixes"


async def editor_pass_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Editor pass for consistency and voice harmonization.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    
    # Build draft objects
    drafts = {}
    for section_id, draft_data in state.get("drafts", {}).items():
        drafts[section_id] = SectionDraft(**draft_data)
    
    # Run editor
    edited_drafts, changes_made = await edit_sections(drafts, newsletter_state)
    
    # Update state
    updated_drafts = {}
    for section_id, draft in edited_drafts.items():
        updated_drafts[section_id] = draft.model_dump()
    
    return {
        "drafts": updated_drafts,
        "editor_changes": changes_made,
    }


def assemble_newsletter_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assemble final newsletter markdown from sections.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    drafts = state.get("drafts", {})
    evidence_packs = state.get("evidence_packs", {})
    
    # Build newsletter markdown
    lines = [
        f"# Digital Infrastructure Weekly — {newsletter_state.time_window.end.isoformat()}",
        "",
        f"_Time window: {newsletter_state.time_window.start.isoformat()} to {newsletter_state.time_window.end.isoformat()}_  ",
        f"_Voice: {newsletter_state.voice_profile}_",
        "",
        "---",
        "",
    ]
    
    for vertical in newsletter_state.verticals:
        section_id = vertical.value
        if section_id in drafts:
            draft = SectionDraft(**drafts[section_id])
            # Get evidence pack for this section if available
            evidence_pack = None
            if section_id in evidence_packs:
                evidence_pack = EvidencePack(**evidence_packs[section_id])
            
            display_name = VERTICAL_DISPLAY_NAMES.get(vertical, section_id)
            
            lines.append(f"## {display_name}")
            lines.append("")
            lines.append(draft.to_markdown(evidence_pack))
            lines.append("")
            lines.append("---")
            lines.append("")
    
    newsletter_md = "\n".join(lines)
    
    return {"newsletter_md": newsletter_md}


async def persist_artifacts_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist all artifacts to filesystem.
    """
    newsletter_state = NewsletterState(**state["newsletter_state"])
    
    # Initialize store
    store = ArtifactStore()
    newsletter_id = newsletter_state.run_id
    
    # Persist newsletter markdown
    newsletter_md = state.get("newsletter_md", "")
    newsletter_path = store.write_newsletter(newsletter_id, newsletter_md)
    
    # Persist sections
    section_paths = {}
    for section_id, draft_data in state.get("drafts", {}).items():
        draft = SectionDraft(**draft_data)
        paths = store.write_section(newsletter_id, section_id, draft)
        section_paths[section_id] = paths
    
    # Persist evidence packs
    evidence_paths = {}
    for section_id, pack_data in state.get("evidence_packs", {}).items():
        evidence_pack = EvidencePack(**pack_data)
        path = store.write_evidence_pack(newsletter_id, section_id, evidence_pack)
        evidence_paths[section_id] = path
    
    # Persist reviews
    review_paths = {}
    for section_id, reviews in state.get("reviews", {}).items():
        paths = store.write_reviews(newsletter_id, section_id, reviews)
        review_paths[section_id] = paths
    
    # Persist metadata
    meta_path = store.write_metadata(newsletter_id, newsletter_state, state)
    
    # Update state with paths
    output_paths = {
        "newsletter_md": newsletter_path,
        "sections": section_paths,
        "evidence": evidence_paths,
        "reviews": review_paths,
        "meta": meta_path,
    }
    
    return {"output_paths": output_paths}
