"""Reviewer agent - scores drafts and produces fix plans."""

from typing import Optional
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.evidence import EvidencePack
from ..schemas.sections import SectionDraft, ReviewScore, FixPlan, FixAction, ReviewResult
from ..constants import GROUNDING_THRESHOLD, CLARITY_THRESHOLD


REVIEWER_PROMPT = """You are a senior editor reviewing a newsletter section draft.

## Review Rubric (Score 0-5 for each)

1. **Grounding**: How well are claims supported by evidence?
   - 5: All claims have strong, relevant citations
   - 4: Most claims are well-supported with minor gaps
   - 3: Some claims lack proper evidence support
   - 2: Multiple unsupported claims
   - 1: Mostly unsupported content
   - 0: No evidence citations

2. **Clarity**: Is the writing concise and comprehensible?
   - 5: Exceptionally clear and well-structured
   - 4: Clear with good flow
   - 3: Generally understandable but could be cleaner
   - 2: Confusing in parts
   - 1: Very difficult to follow
   - 0: Incomprehensible

3. **Newsworthiness**: Is the content timely and important?
   - 5: Highly relevant, timely developments
   - 4: Good selection of notable news
   - 3: Adequate coverage of sector
   - 2: Missing major stories
   - 1: Outdated or irrelevant content
   - 0: No newsworthy content

4. **Balance**: Avoids hype, includes caveats where relevant?
   - 5: Perfectly balanced, appropriately caveated
   - 4: Well-balanced with good perspective
   - 3: Reasonable balance
   - 2: Somewhat one-sided or hyped
   - 1: Clearly biased or promotional
   - 0: Pure hype or propaganda

5. **Voice Fit**: Does the tone match the requested voice?
   - Target voice: {voice_profile}
   - 5: Perfect match to voice
   - 4: Good fit with minor deviations
   - 3: Acceptable but inconsistent
   - 2: Often misses the mark
   - 1: Wrong tone throughout
   - 0: Completely wrong voice

## Acceptance Requirements
- Grounding ≥ 4
- Clarity ≥ 4
- No blocking issues (unsupported claims, duplicated bullets)

## Section Draft to Review
{draft_json}

## Available Evidence
{evidence_summary}

## Output Format
Respond with JSON:
{{
  "scores": {{
    "grounding": 4,
    "clarity": 5,
    "newsworthiness": 4,
    "balance": 4,
    "voice_fit": 4
  }},
  "issues": [
    "Description of issue 1",
    "Description of issue 2"
  ],
  "fix_actions": [
    {{
      "action_type": "fetch_source|rewrite|add_citation|clarify|adjust_tone",
      "description": "What needs to be done",
      "target": "bullet_1 or paragraph",
      "suggested_tool": "web_search or fetch_article or null",
      "suggested_query": "Search query if applicable"
    }}
  ],
  "accepted": true,
  "notes": "Optional reviewer notes"
}}
"""


def create_reviewer_agent():
    """Create the reviewer agent."""
    settings = get_settings()
    
    return ChatOpenAI(
        model=settings.model_review,
        api_key=settings.openai_api_key,
        temperature=0,  # Consistent scoring
    )


async def review_section(
    draft: SectionDraft,
    evidence_pack: EvidencePack,
    state: NewsletterState,
    review_round: int,
) -> ReviewResult:
    """
    Review a section draft and produce scores and fix plan.
    
    Args:
        draft: The section draft to review.
        evidence_pack: Evidence pack for the section.
        state: Current newsletter state.
        review_round: Current review iteration number.
    
    Returns:
        ReviewResult with scores, issues, and fix plan.
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_review,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    
    # Prepare draft JSON
    draft_json = json.dumps({
        "section_id": draft.section_id,
        "big_picture": draft.big_picture,
        "big_picture_evidence_ids": draft.big_picture_evidence_ids,
        "bullets": [
            {
                "text": b.text,
                "evidence_ids": b.evidence_ids,
                "player_referenced": b.player_referenced,
            }
            for b in draft.bullets
        ],
        "risk_flags": draft.risk_flags,
    }, indent=2)
    
    # Prepare evidence summary
    evidence_summary = "\n".join([
        f"- {item.evidence_id}: {item.title or 'No title'} ({item.source_name})"
        for item in evidence_pack.items
    ])
    
    prompt = REVIEWER_PROMPT.format(
        voice_profile=state.voice_profile,
        draft_json=draft_json,
        evidence_summary=evidence_summary,
    )
    
    system_msg = SystemMessage(content=prompt)
    human_msg = HumanMessage(content="Please review this section and provide your assessment.")
    
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
        # Return failing review on parse error
        return ReviewResult(
            section_id=draft.section_id,
            review_round=review_round,
            scores=ReviewScore(
                grounding=0,
                clarity=0,
                newsworthiness=0,
                balance=0,
                voice_fit=0,
            ),
            issues=["Review parsing failed"],
            accepted=False,
            notes="LLM response could not be parsed",
        )
    
    # Build scores
    scores_data = parsed.get("scores", {})
    scores = ReviewScore(
        grounding=scores_data.get("grounding", 0),
        clarity=scores_data.get("clarity", 0),
        newsworthiness=scores_data.get("newsworthiness", 0),
        balance=scores_data.get("balance", 0),
        voice_fit=scores_data.get("voice_fit", 0),
    )
    
    # Build fix actions
    fix_actions = []
    for action_data in parsed.get("fix_actions", []):
        fix_actions.append(FixAction(
            action_type=action_data.get("action_type", "rewrite"),
            description=action_data.get("description", ""),
            target=action_data.get("target"),
            suggested_tool=action_data.get("suggested_tool"),
            suggested_query=action_data.get("suggested_query"),
        ))
    
    # Determine acceptance
    issues = parsed.get("issues", [])
    accepted = parsed.get("accepted", False)
    
    # Override acceptance based on thresholds
    if not scores.passes_threshold(GROUNDING_THRESHOLD, CLARITY_THRESHOLD):
        accepted = False
    
    # Build fix plan if not accepted
    fix_plan = None
    if not accepted and fix_actions:
        fix_plan = FixPlan(
            section_id=draft.section_id,
            target_agent=f"research_{draft.section_id}",
            issues=issues,
            actions=fix_actions,
            blocking=True,
        )
    
    return ReviewResult(
        section_id=draft.section_id,
        review_round=review_round,
        scores=scores,
        issues=issues,
        fix_plan=fix_plan,
        accepted=accepted,
        notes=parsed.get("notes"),
    )
