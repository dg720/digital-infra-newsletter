"""Editor agent - performs minor voice/consistency pass."""

from typing import Dict
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.sections import SectionDraft, Bullet
from ..utils.citations import normalize_evidence_ids, strip_evidence_markers


EDITOR_PROMPT = """You are a newsletter editor performing a final polish pass.

## Your Task
Make minor edits to ensure consistency across all sections:
- Harmonize tone and voice across sections
- Shorten or rearrange sentences for readability
- Fix any stylistic inconsistencies
- Ensure consistent formatting
- Create a short, punchy headline for each section that captures the main theme

## Critical Constraints
- DO NOT add new facts or claims
- DO NOT remove evidence citations
- DO NOT change the substance or meaning of any claim
- If you find an unsupported claim, flag it in your response - do not silently "fix" it

## Voice Profile
{voice_profile}

## Style Guidelines
{style_prompt}

## Sections to Edit
{sections_json}

## Output Format
Return the edited sections in JSON format:
{{
  "sections": {{
    "data_centers": {{
      "headline": "Short punchy headline...",
      "big_picture": "Edited paragraph...",
      "big_picture_evidence_ids": ["ev_xxx"],
      "bullets": [
        {{"text": "Edited bullet", "evidence_ids": ["ev_xxx"], "player_referenced": "Company"}}
      ]
    }},
    // ... other sections
  }},
  "changes_made": [
    "Shortened paragraph in data_centers section",
    "Harmonized tense in towers_wireless bullets"
  ],
  "unsupported_claims_found": []
}}
"""


def create_editor_agent():
    """Create the editor agent."""
    settings = get_settings()
    
    return ChatOpenAI(
        model=settings.model_edit,
        api_key=settings.openai_api_key,
        temperature=0.2,  # Slight creativity for style
    )


async def edit_sections(
    drafts: Dict[str, SectionDraft],
    state: NewsletterState,
) -> tuple[Dict[str, SectionDraft], list[str]]:
    """
    Perform editorial pass on all section drafts.
    
    Args:
        drafts: Dictionary of section_id -> SectionDraft.
        state: Current newsletter state.
    
    Returns:
        Tuple of (edited drafts dict, list of changes made).
    
    Raises:
        ValueError: If unsupported claims are found during editing.
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_edit,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    
    # Prepare sections JSON
    sections_json = json.dumps({
        section_id: {
            "headline": draft.headline,
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
        }
        for section_id, draft in drafts.items()
    }, indent=2)
    
    prompt = EDITOR_PROMPT.format(
        voice_profile=state.voice_profile,
        style_prompt=state.style_prompt or "No additional style guidelines",
        sections_json=sections_json,
    )
    
    system_msg = SystemMessage(content=prompt)
    human_msg = HumanMessage(content="Please edit these sections for consistency.")
    
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
        # Return original drafts on parse error
        return drafts, ["Editor pass skipped - parsing error"]
    
    # Check for unsupported claims
    unsupported = parsed.get("unsupported_claims_found", [])
    if unsupported:
        raise ValueError(f"Editor found unsupported claims: {unsupported}")
    
    # Build edited drafts
    edited_drafts = {}
    sections_data = parsed.get("sections", {})
    
    for section_id, draft in drafts.items():
        if section_id in sections_data:
            edited_data = sections_data[section_id]
            headline_value = edited_data.get("headline", draft.headline)
            if isinstance(headline_value, str):
                headline_value = strip_evidence_markers(headline_value).strip() or None
            
            # Build bullets, preserving evidence IDs if the editor drops them
            bullets = []
            edited_bullets = edited_data.get("bullets", [])
            for idx, b in enumerate(edited_bullets):
                original_bullet = draft.bullets[idx] if idx < len(draft.bullets) else None
                evidence_ids = normalize_evidence_ids(b.get("evidence_ids", []))
                if not evidence_ids and original_bullet:
                    evidence_ids = original_bullet.evidence_ids
                text_value = b.get("text", original_bullet.text if original_bullet else "")
                bullets.append(Bullet(
                    text=strip_evidence_markers(text_value),
                    evidence_ids=evidence_ids,
                    player_referenced=b.get(
                        "player_referenced",
                        original_bullet.player_referenced if original_bullet else None,
                    ),
                ))
            
            edited_drafts[section_id] = SectionDraft(
                section_id=section_id,
                headline=headline_value,
                big_picture=strip_evidence_markers(
                    edited_data.get("big_picture", draft.big_picture)
                ),
                big_picture_evidence_ids=(
                    normalize_evidence_ids(edited_data.get("big_picture_evidence_ids"))
                    or draft.big_picture_evidence_ids
                ),
                bullets=bullets if bullets else draft.bullets,
                risk_flags=draft.risk_flags,  # Preserve original flags
            )
        else:
            # Keep original if not in edited output
            edited_drafts[section_id] = draft
    
    changes_made = parsed.get("changes_made", [])
    
    return edited_drafts, changes_made
