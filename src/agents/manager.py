"""Manager agent - orchestrates workflow and parses natural language input."""

from datetime import date, timedelta
from typing import Optional, Dict, Any
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import TimeWindow, ParsedInput, NewsletterState
from ..constants import Vertical, MAJOR_PLAYERS, DEFAULT_EVIDENCE_BUDGET, DEFAULT_MAX_REVIEW_ROUNDS


# System prompt for parsing natural language input
MANAGER_PARSE_PROMPT = """You are an assistant that parses natural language requests into structured newsletter parameters.

Given a user's request to generate a digital infrastructure newsletter, extract the following fields:

1. **time_window**: The date range for news coverage.
   - Look for phrases like "last week", "past 7 days", "last month", "from Jan 1 to Jan 15"
   - Default: last 7 days ending today if not specified
   - Current date for reference: {current_date}

2. **verticals**: Which sectors to include. Valid options are:
   - "data_centers" - Data center infrastructure news
   - "connectivity_fibre" - Connectivity and fibre network news  
   - "towers_wireless" - Towers and wireless infrastructure news
   - Default: all three if not specified

3. **voice_profile**: The desired tone/voice.
   - Examples: "expert_operator" (technical, professional), "conversational", "academic", "executive_brief"
   - Default: "expert_operator" if not specified

4. **region_focus**: Geographic focus if any.
   - Examples: "UK", "EU", "US", "Asia", "global"
   - Default: null (global) if not specified

5. **style_prompt**: Any additional style instructions.
   - Extract any freeform guidance about writing style
   - Default: null if not specified

Respond with a JSON object containing these fields. Use the exact field names shown.
For dates, use ISO format (YYYY-MM-DD).

Example response:
{{
  "time_window": {{"start": "2026-01-26", "end": "2026-02-02"}},
  "verticals": ["data_centers", "connectivity_fibre"],
  "voice_profile": "conversational",
  "region_focus": "UK",
  "style_prompt": "Keep it brief and punchy"
}}
"""


def parse_natural_language_input(
    prompt: str,
    current_date: Optional[date] = None,
) -> ParsedInput:
    """
    Parse a natural language prompt into structured newsletter parameters.
    
    Args:
        prompt: The user's natural language request.
        current_date: Current date for interpreting relative dates. Defaults to today.
    
    Returns:
        ParsedInput with extracted/defaulted fields.
    """
    settings = get_settings()
    
    if current_date is None:
        current_date = date.today()
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=settings.model_manager,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    
    # Build messages
    system_msg = SystemMessage(content=MANAGER_PARSE_PROMPT.format(
        current_date=current_date.isoformat()
    ))
    human_msg = HumanMessage(content=f"Parse this request:\n\n{prompt}")
    
    # Call LLM
    response = llm.invoke([system_msg, human_msg])
    
    # Parse response
    try:
        # Extract JSON from response
        content = response.content
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        parsed = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        # Fall back to defaults
        parsed = {}
    
    # Build TimeWindow with defaults
    if "time_window" in parsed and parsed["time_window"]:
        tw = parsed["time_window"]
        time_window = TimeWindow(
            start=date.fromisoformat(tw["start"]),
            end=date.fromisoformat(tw["end"]),
        )
    else:
        # Default: last 7 days
        time_window = TimeWindow(
            start=current_date - timedelta(days=7),
            end=current_date,
        )
    
    # Parse verticals
    verticals = []
    if "verticals" in parsed and parsed["verticals"]:
        for v in parsed["verticals"]:
            try:
                verticals.append(Vertical(v))
            except ValueError:
                pass
    if not verticals:
        verticals = list(Vertical)
    
    return ParsedInput(
        time_window=time_window,
        verticals=verticals,
        voice_profile=parsed.get("voice_profile", "expert_operator"),
        region_focus=parsed.get("region_focus"),
        style_prompt=parsed.get("style_prompt"),
    )


def create_initial_state(
    prompt: str,
    parsed_input: ParsedInput,
    max_review_rounds: int = DEFAULT_MAX_REVIEW_ROUNDS,
) -> NewsletterState:
    """
    Create the initial newsletter state from parsed input.
    
    Args:
        prompt: Original user prompt.
        parsed_input: Parsed structured input.
        max_review_rounds: Maximum review iterations.
    
    Returns:
        Initialized NewsletterState.
    """
    settings = get_settings()
    
    # Build comps dictionary from major players
    comps = {v.value: MAJOR_PLAYERS[v] for v in parsed_input.verticals}
    
    # Build evidence budgets
    evidence_budgets = {v.value: DEFAULT_EVIDENCE_BUDGET for v in parsed_input.verticals}
    
    return NewsletterState(
        mode="generate_issue",
        time_window=parsed_input.time_window,
        verticals=parsed_input.verticals,
        voice_profile=parsed_input.voice_profile,
        region_focus=parsed_input.region_focus,
        style_prompt=parsed_input.style_prompt,
        comps=comps,
        evidence_budgets=evidence_budgets,
        max_review_rounds=max_review_rounds,
        original_prompt=prompt,
        model_versions={
            "manager": settings.model_manager,
            "research": settings.model_research,
            "review": settings.model_review,
            "edit": settings.model_edit,
        },
    )


def create_manager_agent():
    """Create the manager agent for orchestrating the workflow."""
    settings = get_settings()
    
    return ChatOpenAI(
        model=settings.model_manager,
        api_key=settings.openai_api_key,
        temperature=0,
    )
