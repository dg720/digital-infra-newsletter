"""FastAPI application for Digital Infrastructure Newsletter."""

import json
import os
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .schemas.api import (
    GenerateRequest,
    GenerateResponse,
    UpdateSectionRequest,
    UpdateSectionResponse,
)
from .schemas.state import NewsletterState, TimeWindow
from .schemas.sections import SectionDraft
from .schemas.evidence import EvidencePack
from .workflow.graph import run_newsletter_generation
from .storage.artifacts import ArtifactStore
from .constants import Vertical
from .agents.research import research_vertical
from .agents.reviewer import review_section
from .agents.editor import edit_sections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Digital Infrastructure Newsletter API starting...")
    yield
    # Shutdown
    print("API shutting down...")


app = FastAPI(
    title="Digital Infrastructure Newsletter",
    description="Automated newsletter generation using LangGraph multi-agent workflow",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow frontend access
default_cors = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
cors_env = os.environ.get("CORS_ORIGINS")
allow_origins = [o.strip() for o in cors_env.split(",")] if cors_env else default_cors

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_event(event: str, data: dict) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def generate_newsletter_stream(
    prompt: str,
    max_review_rounds: int = 2,
    active_players: dict = None,
) -> AsyncGenerator[str, None]:
    """Stream generation progress via SSE with real workflow updates."""
    from .workflow.graph import run_newsletter_generation_streaming
    
    try:
        # Use the streaming version that yields progress updates
        async for event in run_newsletter_generation_streaming(
            prompt=prompt,
            max_review_rounds=max_review_rounds,
            active_players=active_players,
        ):
            event_type = event.get("type", "status")
            
            if event_type == "status":
                yield sse_event("status", {
                    "step": event.get("step", "unknown"),
                    "message": event.get("message", "Processing..."),
                    "status": event.get("status", "start"),
                })
            elif event_type == "debug":
                yield sse_event("debug", {
                    "category": event.get("category", "unknown"),
                    "content": event.get("content", ""),
                    "metadata": event.get("metadata", {}),
                })
            elif event_type == "complete":
                yield sse_event("complete", {
                    "newsletter_id": event.get("newsletter_id"),
                    "paths": event.get("paths", {}),
                    "status": "completed",
                })
            elif event_type == "error":
                yield sse_event("error", {"message": event.get("message", "Unknown error")})
                
    except Exception as e:
        yield sse_event("error", {"message": str(e)})


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "digital-infra-newsletter"}


@app.post("/newsletter/generate", response_model=GenerateResponse)
async def generate_newsletter(request: GenerateRequest) -> GenerateResponse:
    """
    Generate a full newsletter issue from a natural language prompt.
    
    The manager agent parses your prompt to extract:
    - Time window (e.g., "last week", "past 7 days")
    - Verticals to include (data centers, connectivity, towers)
    - Voice/tone preferences
    - Region focus (optional)
    - Style instructions (optional)
    
    Example prompts:
    - "Generate a newsletter for the last week"
    - "Summarise data centre and fibre news from the UK for the past 10 days"
    - "Create a conversational newsletter about tower infrastructure in Europe"
    """
    try:
        # Run the workflow
        result = await run_newsletter_generation(
            prompt=request.prompt,
            max_review_rounds=request.max_review_rounds,
        )
        
        # Extract newsletter ID and paths
        newsletter_state = result.get("newsletter_state", {})
        newsletter_id = newsletter_state.get("run_id", "unknown")
        output_paths = result.get("output_paths", {})
        
        return GenerateResponse(
            newsletter_id=newsletter_id,
            paths={
                "newsletter_md": output_paths.get("newsletter_md", ""),
                "meta": output_paths.get("meta", ""),
            },
            status="completed",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/newsletter/generate/stream")
async def generate_newsletter_streaming(request: GenerateRequest):
    """
    Generate a newsletter with SSE streaming progress updates.
    """
    return StreamingResponse(
        generate_newsletter_stream(
            request.prompt, 
            request.max_review_rounds,
            request.active_players
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/newsletter/{newsletter_id}/update-section", response_model=UpdateSectionResponse)
async def update_section(
    newsletter_id: str,
    request: UpdateSectionRequest,
) -> UpdateSectionResponse:
    """
    Update a specific section of an existing newsletter.
    
    Takes an instruction describing the desired changes and regenerates
    the specified section while preserving the rest of the newsletter.
    """
    store = ArtifactStore()
    
    # Check if newsletter exists
    if not store.read_newsletter(newsletter_id):
        raise HTTPException(status_code=404, detail=f"Newsletter {newsletter_id} not found")
    
    # Map section IDs
    section_id_map = {
        "data_centers": Vertical.DATA_CENTERS,
        "connectivity_fibre": Vertical.CONNECTIVITY_FIBRE,
        "towers_wireless": Vertical.TOWERS_WIRELESS,
    }
    
    if request.section_id not in section_id_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section_id. Must be one of: {list(section_id_map.keys())}"
        )
    
    vertical = section_id_map[request.section_id]
    
    try:
        # Load existing metadata
        meta = store.read_artifact(newsletter_id, "meta.json")
        if not meta:
            raise HTTPException(status_code=404, detail="Newsletter metadata not found")
        
        # Reconstruct state from metadata
        from datetime import date
        newsletter_state = NewsletterState(
            run_id=newsletter_id,
            time_window=TimeWindow(
                start=date.fromisoformat(meta["time_window"]["start"]),
                end=date.fromisoformat(meta["time_window"]["end"]),
            ),
            voice_profile=meta.get("voice_profile", "expert_operator"),
            region_focus=meta.get("region_focus"),
            style_prompt=request.instruction,  # Use the instruction as additional context
            original_prompt=meta.get("original_prompt", ""),
        )
        
        # Re-research the section with the new instruction
        evidence_pack, draft = await research_vertical(vertical, newsletter_state)
        
        # Review the new draft
        review_result = await review_section(
            draft=draft,
            evidence_pack=evidence_pack,
            state=newsletter_state,
            review_round=1,
        )
        
        # Apply editor pass
        edited_drafts, changes_made = await edit_sections(
            {request.section_id: draft},
            newsletter_state,
        )
        
        final_draft = edited_drafts.get(request.section_id, draft)
        
        # Persist updated section
        store.write_section(newsletter_id, request.section_id, final_draft)
        store.write_evidence_pack(newsletter_id, request.section_id, evidence_pack)
        
        # Update the newsletter markdown
        existing_md = store.read_newsletter(newsletter_id)
        if existing_md:
            # Regenerate full newsletter with updated section
            all_drafts = {}
            all_evidence = {}
            for section_id in section_id_map.keys():
                section_data = store.read_artifact(newsletter_id, f"sections/{section_id}.json")
                if section_data:
                    all_drafts[section_id] = SectionDraft(**section_data)
                evidence_data = store.read_artifact(newsletter_id, f"evidence/{section_id}_pack.json")
                if evidence_data:
                    all_evidence[section_id] = EvidencePack(**evidence_data)
            
            # Replace the updated section and evidence
            all_drafts[request.section_id] = final_draft
            all_evidence[request.section_id] = evidence_pack
            
            # Reassemble newsletter
            from .constants import VERTICAL_DISPLAY_NAMES
            lines = [
                f"# Digital Infrastructure Weekly — {newsletter_state.time_window.end.isoformat()}",
                "",
                f"_Time window: {newsletter_state.time_window.start.isoformat()} to {newsletter_state.time_window.end.isoformat()}_  ",
                f"_Voice: {newsletter_state.voice_profile}_",
                "",
                "---",
                "",
            ]
            
            for sid, v in section_id_map.items():
                if sid in all_drafts:
                    display_name = VERTICAL_DISPLAY_NAMES.get(v, sid)
                    ep = all_evidence.get(sid)
                    lines.append(f"## {display_name}")
                    lines.append("")
                    lines.append(all_drafts[sid].to_markdown(ep))
                    lines.append("")
                    lines.append("---")
                    lines.append("")
            
            new_md = "\n".join(lines)
            store.write_newsletter(newsletter_id, new_md)
        
        # Log the change
        store.write_changelog(newsletter_id, [{
            "action": "update_section",
            "section_id": request.section_id,
            "instruction": request.instruction,
            "changes": changes_made,
        }])
        
        return UpdateSectionResponse(
            newsletter_id=newsletter_id,
            section_id=request.section_id,
            status="updated",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/newsletter/{newsletter_id}", response_class=PlainTextResponse)
async def get_newsletter(newsletter_id: str) -> str:
    """
    Retrieve the generated newsletter markdown.
    """
    store = ArtifactStore()
    content = store.read_newsletter(newsletter_id)
    
    if content is None:
        raise HTTPException(status_code=404, detail=f"Newsletter {newsletter_id} not found")
    
    return content


@app.get("/newsletter/{newsletter_id}/sections/{section_id}", response_class=PlainTextResponse)
async def get_section(newsletter_id: str, section_id: str) -> str:
    """
    Retrieve a specific section markdown.
    """
    store = ArtifactStore()
    content = store.read_section(newsletter_id, section_id)
    
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {section_id} not found in newsletter {newsletter_id}"
        )
    
    return content


@app.get("/newsletter/{newsletter_id}/artifacts/{artifact_path:path}")
async def get_artifact(newsletter_id: str, artifact_path: str):
    """
    Retrieve a JSON artifact (evidence pack, review, etc.) by path.
    
    Example paths:
    - evidence/data_centers_pack.json
    - reviews/connectivity_fibre_review_round_1.json
    - meta.json
    """
    store = ArtifactStore()
    content = store.read_artifact(newsletter_id, artifact_path)
    
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_path} not found in newsletter {newsletter_id}"
        )
    
    return content


@app.get("/newsletters")
async def list_newsletters():
    """
    List all generated newsletter IDs.
    """
    store = ArtifactStore()
    issues = store.list_issues()
    return {"newsletters": issues, "count": len(issues)}


@app.delete("/newsletter/{newsletter_id}")
async def delete_newsletter(newsletter_id: str):
    """
    Delete a newsletter issue and all its artifacts.
    """
    store = ArtifactStore()
    
    if not store.read_newsletter(newsletter_id):
        raise HTTPException(status_code=404, detail=f"Newsletter {newsletter_id} not found")
    
    deleted = store.delete_issue(newsletter_id)
    if deleted:
        return {"status": "deleted", "newsletter_id": newsletter_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete newsletter")
