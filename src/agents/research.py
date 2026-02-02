"""Research agents - vertical specialists that gather evidence and draft sections."""

from typing import List, Optional
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
3. Create up to 5 bullet points highlighting major player updates

## Major Players to Prioritize
{major_players}

## Guidelines
- Every claim MUST be supported by evidence from the provided sources
- Reference evidence by their evidence_id in your draft
- Focus on news within the time window: {start_date} to {end_date}
- Voice/Tone: {voice_profile}
- Region Focus: {region_focus}
{style_instructions}

## Output Format
Respond with a JSON object:
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
    players = MAJOR_PLAYERS.get(vertical, [])
    for player in players[:5]:  # Top 5 players
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
    
    for query in queries:
        if call_count >= max_calls:
            break
        
        # Execute web search
        results = web_search(
            query=query,
            max_results=5,
            time_window_days=time_window_days,
        )
        call_count += 1
        
        for item in results:
            evidence_pack.add_item(item)
    
    # Optionally fetch full articles for top results
    urls_to_fetch = []
    for item in evidence_pack.items[:3]:  # Top 3 most relevant
        if item.url and call_count < max_calls:
            urls_to_fetch.append(item.url)
    
    for url in urls_to_fetch:
        if call_count >= max_calls:
            break
        fetched = fetch_article(url)
        if fetched:
            evidence_pack.add_item(fetched)
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
    
    # Build prompt
    major_players_str = "\n".join(f"- {p}" for p in MAJOR_PLAYERS.get(vertical, []))
    
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
    
    # Build bullets
    bullets = []
    for b in parsed.get("bullets", [])[:5]:  # Max 5 bullets
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
