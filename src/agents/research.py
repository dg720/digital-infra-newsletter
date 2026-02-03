"""Research agents - vertical specialists that gather evidence and draft sections."""

from typing import List, Optional
import asyncio
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.evidence import EvidenceItem, EvidencePack
from ..schemas.sections import SectionDraft, Bullet
from ..constants import Vertical, MAJOR_PLAYERS, SECTOR_KEYWORDS, VERTICAL_DISPLAY_NAMES
from ..tools import web_search, fetch_article


# System prompt template for research agents
RESEARCH_AGENT_PROMPT = """You are a research analyst specializing in {vertical_name} infrastructure.

Your task is to research recent news and developments in the {vertical_name} sector and draft a newsletter section.

## Your Mission
1. Analyze the provided evidence about {vertical_name} news
2. Draft a big-picture paragraph summarizing key themes (80-140 words)
3. Create EXACTLY {bullet_count} bullet points - no more, no less

## CRITICAL CONSTRAINTS
- You MUST create exactly {bullet_count} bullets. Not 3, not 5 - EXACTLY {bullet_count}.
- ONLY reference the following companies. Do NOT mention any other companies:
{major_players}

## Guidelines
- Every claim MUST be supported by evidence from the provided sources
- Reference evidence by their evidence_id in your draft
- Focus on news within the time window: {start_date} to {end_date}
- Voice/Tone: {voice_profile}
- Region Focus: {region_focus}
{style_instructions}

## Output Format
Respond with a JSON object containing EXACTLY {bullet_count} bullets:
{{
  "big_picture": "Your 80-140 word summary paragraph here...",
  "big_picture_evidence_ids": ["ev_xxx", "ev_yyy"],
  "bullets": [
    {{
      "text": "Bullet text here",
      "evidence_ids": ["ev_xxx"],
      "player_referenced": "Company Name or null"
    }}
  ],
  "risk_flags": ["Any uncertainties or gaps in coverage"]
}}

## Evidence to Analyze
{evidence_json}
"""


def create_research_agent(vertical: Vertical):
    """Create a research agent for a specific vertical."""
    settings = get_settings()
    
    return ChatOpenAI(
        model=settings.model_research,
        api_key=settings.openai_api_key,
        temperature=0.3,  # Slight creativity for writing
    )


def generate_search_queries(
    vertical: Vertical,
    state: NewsletterState,
) -> List[str]:
    """Generate initial search queries for a vertical based on state."""
    queries = []
    
    # Add sector keyword queries
    keywords = SECTOR_KEYWORDS.get(vertical, [])
    for kw in keywords[:3]:  # Limit initial queries
        query = f"{kw} {state.time_window.end.year}"
        if state.region_focus:
            query = f"{query} {state.region_focus}"
        queries.append(query)
    
    # Add major player queries
    if state.comps and vertical.value in state.comps:
        players = state.comps[vertical.value]
    else:
        players = MAJOR_PLAYERS.get(vertical, [])
        # Default behavior: limit to top 5 if using default list
        players = players[:5]
        
    for player in players:
        query = f"{player} news"
        if state.region_focus:
            query = f"{query} {state.region_focus}"
        queries.append(query)
    
    return queries


async def research_vertical(
    vertical: Vertical,
    state: NewsletterState,
) -> tuple[EvidencePack, SectionDraft]:
    """
    Research a vertical and produce evidence pack + draft section.
    
    Args:
        vertical: The vertical to research.
        state: Current newsletter state.
    
    Returns:
        Tuple of (EvidencePack, SectionDraft).
    """
    settings = get_settings()
    section_id = vertical.value
    
    # Initialize evidence pack
    evidence_pack = EvidencePack(section_id=section_id)
    
    # Generate and execute search queries
    queries = generate_search_queries(vertical, state)
    time_window_days = state.time_window.days() + 1  # Include buffer
    
    call_count = 0
    max_calls = state.evidence_budgets.get(section_id, 12)
    
    # 1. Parallelize Search Queries
    # -----------------------------
    # Trim queries to budget if needed (keeping some buffer for fetching)
    search_budget = max(1, max_calls - 3) # Reserve ~3 calls for article fetching
    if len(queries) > search_budget:
        queries = queries[:search_budget]
    
    loop = asyncio.get_running_loop()
    search_tasks = []
    
    for query in queries:
        search_tasks.append(
            loop.run_in_executor(None, web_search, query, 5, time_window_days)
        )
        
    if search_tasks:
        search_results_list = await asyncio.gather(*search_tasks)
        call_count += len(search_tasks)
        
        for results in search_results_list:
            for item in results:
                evidence_pack.add_item(item)

    # 2. Parallelize Article Fetching
    # -------------------------------
    urls_to_fetch = []
    remaining_budget = max_calls - call_count
    
    if remaining_budget > 0:
        # Prioritize items that have a URL and aren't already full text
        candidates = [item for item in evidence_pack.items if item.url and not item.text]
        # Sort by relevance or just take top ones (evidence_pack already likely has them in order)
        
        for item in candidates[:3]:  # Limit to top 3 articles max
            urls_to_fetch.append(item.url)
            
        if len(urls_to_fetch) > remaining_budget:
            urls_to_fetch = urls_to_fetch[:remaining_budget]
            
        if urls_to_fetch:
            fetch_tasks = [
                loop.run_in_executor(None, fetch_article, url) 
                for url in urls_to_fetch
            ]
            
            fetched_items = await asyncio.gather(*fetch_tasks)
            
            for item in fetched_items:
                if item:
                    evidence_pack.add_item(item)
                    call_count += 1
    
    # Now draft the section using LLM
    draft = await _draft_section(vertical, state, evidence_pack)
    
    return evidence_pack, draft


async def _draft_section(
    vertical: Vertical,
    state: NewsletterState,
    evidence_pack: EvidencePack,
) -> SectionDraft:
    """Use LLM to draft a section from evidence."""
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_research,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    
    # Get active players for this vertical - use state.comps if set, otherwise MAJOR_PLAYERS
    section_id = vertical.value
    if state.comps and section_id in state.comps:
        active_players = state.comps[section_id]
    else:
        active_players = MAJOR_PLAYERS.get(vertical, [])
    
    # Bullet count matches the number of active players (max 5)
    bullet_count = min(len(active_players), 5) if active_players else 5
    
    # Build prompt using active players, not all players
    major_players_str = "\n".join(f"- {p}" for p in active_players)
    
    style_instructions = ""
    if state.style_prompt:
        style_instructions = f"- Additional style guidance: {state.style_prompt}"
    
    # Serialize evidence for prompt
    evidence_json = json.dumps([
        {
            "evidence_id": item.evidence_id,
            "title": item.title,
            "text": item.text[:1000] if item.text else "",  # Truncate
            "url": item.url,
            "source_name": item.source_name,
        }
        for item in evidence_pack.items
    ], indent=2)
    
    prompt = RESEARCH_AGENT_PROMPT.format(
        vertical_name=VERTICAL_DISPLAY_NAMES.get(vertical, vertical.value),
        major_players=major_players_str,
        bullet_count=bullet_count,
        start_date=state.time_window.start.isoformat(),
        end_date=state.time_window.end.isoformat(),
        voice_profile=state.voice_profile,
        region_focus=state.region_focus or "Global",
        style_instructions=style_instructions,
        evidence_json=evidence_json,
    )
    
    system_msg = SystemMessage(content=prompt)
    human_msg = HumanMessage(content="Please draft the newsletter section based on the evidence provided.")
    
    response = llm.invoke([system_msg, human_msg])
    
    # Parse response
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        parsed = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        # Return minimal draft on parse error
        return SectionDraft(
            section_id=vertical.value,
            big_picture="Unable to generate section - parsing error.",
            big_picture_evidence_ids=[],
            bullets=[],
            risk_flags=["LLM response parsing failed"],
        )
    
    # Build bullets - limit to bullet_count
    bullets = []
    for b in parsed.get("bullets", [])[:bullet_count]:
        bullets.append(Bullet(
            text=b.get("text", ""),
            evidence_ids=b.get("evidence_ids", []),
            player_referenced=b.get("player_referenced"),
        ))
    
    return SectionDraft(
        section_id=vertical.value,
        big_picture=parsed.get("big_picture", ""),
        big_picture_evidence_ids=parsed.get("big_picture_evidence_ids", []),
        bullets=bullets,
        risk_flags=parsed.get("risk_flags", []),
    )

