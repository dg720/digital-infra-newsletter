"""Research agents - vertical specialists that gather evidence and draft sections."""

from typing import List, Optional
from datetime import date, datetime
import re
import asyncio
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.evidence import EvidenceItem, EvidencePack
from ..schemas.sections import SectionDraft, Bullet
from ..constants import Vertical, MAJOR_PLAYERS, SECTOR_KEYWORDS, VERTICAL_DISPLAY_NAMES
from ..utils.citations import extract_evidence_ids, normalize_evidence_ids, strip_evidence_markers
from ..tools import web_search, openai_web_search, fetch_article


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
- Add a short, punchy headline (4-8 words) that captures the main theme

## Output Format
Respond with a JSON object containing EXACTLY {bullet_count} bullets:
{{
  "headline": "Punchy headline here",
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
        if not state.active_players_provided:
            players = players[:5]
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
    strict_dates = state.strict_date_filtering
    
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
    
    search_fn = openai_web_search if state.search_provider == "openai" else web_search

    for query in queries:
        search_tasks.append(
            loop.run_in_executor(None, search_fn, query, 5, time_window_days)
        )
        
    if search_tasks:
        search_results_list = await asyncio.gather(*search_tasks)
        call_count += len(search_tasks)
        
        for results in search_results_list:
            for item in results:
                _ensure_publish_date(item)
                if _is_outside_time_window(
                    item,
                    state.time_window.start,
                    state.time_window.end,
                    require_publish_date=strict_dates,
                ):
                    continue
                evidence_pack.add_item(item)

    # 2. Parallelize Article Fetching + Date Filtering
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
            
            excluded_urls = set()
            for item in fetched_items:
                if not item:
                    continue
                _ensure_publish_date(item)
                if _is_outside_time_window(
                    item,
                    state.time_window.start,
                    state.time_window.end,
                    require_publish_date=strict_dates,
                ):
                    if item.url:
                        excluded_urls.add(item.url)
                    continue
                evidence_pack.add_item(item)
                call_count += 1

            if excluded_urls:
                evidence_pack.items = [
                    existing
                    for existing in evidence_pack.items
                    if existing.url not in excluded_urls
                    and not _is_outside_time_window(
                        existing,
                        state.time_window.start,
                        state.time_window.end,
                        require_publish_date=strict_dates,
                    )
                ]
    
    # Now draft the section using LLM
    draft = await _draft_section(vertical, state, evidence_pack)
    
    return evidence_pack, draft


def _parse_publish_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        return parsed.date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _infer_publish_date_from_text(text: str | None) -> Optional[date]:
    if not text:
        return None
    # Look for phrases like "Published 29 Jan 2023" or "Written Jan 29, 2023"
    month_names = (
        "January|February|March|April|May|June|July|August|September|October|November|December|"
        "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    )
    patterns = [
        rf"(Published|Updated|Written|Posted|Date|On|Last\s+updated|Last\s+modified)\s*[:\-]?\s*(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(20\d{{2}})",
        rf"(Published|Updated|Written|Posted|Date|On|Last\s+updated|Last\s+modified)\s*[:\-]?\s*({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,\s*(20\d{{2}})",
        rf"(Published|Updated|Written|Posted|Date|On|Last\s+updated|Last\s+modified)\s*[:\-]?\s*(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(20\d{{2}})\s+\d{{1,2}}:\d{{2}}",
        rf"(Published|Updated|Written|Posted|Date|On|Last\s+updated|Last\s+modified)\s*[:\-]?\s*({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,\s*(20\d{{2}})\s+\d{{1,2}}:\d{{2}}",
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(20\d{{2}})\b",
        rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,\s*(20\d{{2}})\b",
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(20\d{{2}})\s+\d{{1,2}}:\d{{2}}\b",
        rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,\s*(20\d{{2}})\s+\d{{1,2}}:\d{{2}}\b",
        r"\b(20\d{2})[/-](0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])\b",
        r"\b(20\d{2})\.(0[1-9]|1[0-2])\.(0[1-9]|[12]\d|3[01])\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        parts = match.groups()
        # Normalize to day, month, year order
        if pattern.startswith("(Published") or pattern.startswith("(Updated") or pattern.startswith("(Written") or pattern.startswith("(Posted") or pattern.startswith("(Date") or pattern.startswith("(On") or pattern.startswith("(Last"):
            if parts[1].isdigit():
                day = parts[1]
                month = parts[2]
                year = parts[3]
            else:
                month = parts[1]
                day = parts[2]
                year = parts[3]
        elif pattern.startswith(r"\b(20"):
            year, month, day = parts[0], parts[1], parts[2]
        else:
            if parts[0].isdigit():
                day = parts[0]
                month = parts[1]
                year = parts[2]
            else:
                month = parts[0]
                day = parts[1]
                year = parts[2]
        try:
            # Try full month name first, then abbreviated
            for fmt in ("%d %B %Y", "%d %b %Y"):
                try:
                    return datetime.strptime(f"{day} {month} {year}", fmt).date()
                except ValueError:
                    continue
        except Exception:
            continue
    return None


def _infer_publish_date_for_item(item: EvidenceItem) -> Optional[date]:
    inferred = _infer_publish_date_from_text(item.text)
    if inferred:
        return inferred
    inferred = _infer_publish_date_from_text(item.title)
    if inferred:
        return inferred
    return None


def _extract_publish_date_from_data(item: EvidenceItem) -> Optional[date]:
    if not item.data or not isinstance(item.data, dict):
        return None
    for key in ("publish_date", "published_date", "published", "date", "updated", "last_updated"):
        value = item.data.get(key)
        if isinstance(value, str):
            parsed = _parse_publish_date(value)
            if parsed:
                return parsed
    return None


def _ensure_publish_date(item: EvidenceItem) -> Optional[date]:
    publish_date = _extract_publish_date_from_data(item)
    if publish_date:
        return publish_date
    inferred = _infer_publish_date_for_item(item)
    if inferred:
        if item.data is None:
            item.data = {}
        if isinstance(item.data, dict):
            item.data["publish_date"] = inferred.isoformat()
        return inferred
    return None


def _get_publish_date(item: EvidenceItem) -> Optional[date]:
    publish_date = _extract_publish_date_from_data(item)
    if publish_date:
        return publish_date
    return _infer_publish_date_for_item(item)


def _is_outside_time_window(
    item: EvidenceItem,
    start: date,
    end: date,
    require_publish_date: bool = False,
) -> bool:
    publish_date = _get_publish_date(item)
    if not publish_date:
        return require_publish_date
    return publish_date < start or publish_date > end


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
        print(f"[RESEARCH] Using state.comps for {section_id}: {active_players}")
    else:
        active_players = MAJOR_PLAYERS.get(vertical, [])
        print(f"[RESEARCH] Using MAJOR_PLAYERS for {section_id}: {active_players[:5]}")
    
    # Bullet count matches active players only when explicitly provided
    if state.active_players_provided:
        bullet_count = len(active_players)
    else:
        bullet_count = min(len(active_players), 5)
    print(f"[RESEARCH] {section_id}: bullet_count={bullet_count}, active_players_count={len(active_players)}")
    
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
    
    available_evidence_ids = evidence_pack.get_evidence_ids()
    available_set = set(available_evidence_ids)
    fallback_idx = 0
    auto_assigned = False

    def fallback_ids(count: int = 1) -> list[str]:
        nonlocal fallback_idx, auto_assigned
        if not available_evidence_ids:
            return []
        auto_assigned = True
        picked = []
        for _ in range(count):
            picked.append(available_evidence_ids[fallback_idx % len(available_evidence_ids)])
            fallback_idx += 1
        return picked

    raw_big_picture = parsed.get("big_picture", "")
    headline = parsed.get("headline")
    if isinstance(headline, str):
        headline = strip_evidence_markers(headline).strip() or None
    big_picture_ids = normalize_evidence_ids(parsed.get("big_picture_evidence_ids", []))
    if not big_picture_ids:
        big_picture_ids = extract_evidence_ids(raw_big_picture)
    big_picture_ids = [eid for eid in big_picture_ids if eid in available_set]
    if not big_picture_ids and available_evidence_ids:
        big_picture_ids = fallback_ids(count=min(2, len(available_evidence_ids)))

    # Build bullets - limit to bullet_count
    bullets = []
    for idx, b in enumerate(parsed.get("bullets", [])[:bullet_count]):
        raw_text = b.get("text", "")
        evidence_ids = normalize_evidence_ids(b.get("evidence_ids", []))
        if not evidence_ids:
            evidence_ids = extract_evidence_ids(raw_text)
        evidence_ids = [eid for eid in evidence_ids if eid in available_set]
        if not evidence_ids and available_evidence_ids:
            evidence_ids = fallback_ids()
        bullets.append(Bullet(
            text=strip_evidence_markers(raw_text),
            evidence_ids=evidence_ids,
            player_referenced=b.get("player_referenced"),
        ))
    
    return SectionDraft(
        section_id=vertical.value,
        headline=headline,
        big_picture=strip_evidence_markers(raw_big_picture),
        big_picture_evidence_ids=big_picture_ids,
        bullets=bullets,
        risk_flags=(
            parsed.get("risk_flags", [])
            + (["Auto-assigned evidence IDs due to missing citations."] if auto_assigned else [])
        ),
    )

