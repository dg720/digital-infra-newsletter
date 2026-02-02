"""Editor agent - performs minor voice/consistency pass."""

from typing import Dict
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.sections import SectionDraft, Bullet


EDITOR_PROMPT = """You are a newsletter editor performing a final polish pass.

## Your Task
Make minor edits to ensure consistency across all sections:
- Harmonize tone and voice across sections
- Shorten or rearrange sentences for readability
- Fix any stylistic inconsistencies
- Ensure consistent formatting

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
            
            # Build bullets
            bullets = []
            for b in edited_data.get("bullets", []):
                bullets.append(Bullet(
                    text=b.get("text", ""),
                    evidence_ids=b.get("evidence_ids", []),
                    player_referenced=b.get("player_referenced"),
                ))
            
            edited_drafts[section_id] = SectionDraft(
                section_id=section_id,
                big_picture=edited_data.get("big_picture", draft.big_picture),
                big_picture_evidence_ids=edited_data.get(
                    "big_picture_evidence_ids",
                    draft.big_picture_evidence_ids
                ),
                bullets=bullets if bullets else draft.bullets,
                risk_flags=draft.risk_flags,  # Preserve original flags
            )
        else:
            # Keep original if not in edited output
            edited_drafts[section_id] = draft
    
    changes_made = parsed.get("changes_made", [])
    
    return edited_drafts, changes_made
