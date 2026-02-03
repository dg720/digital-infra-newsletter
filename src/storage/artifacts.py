"""Artifact storage - filesystem-based persistence for newsletter outputs."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..config import get_settings
from ..schemas.state import NewsletterState
from ..schemas.evidence import EvidencePack
from ..schemas.sections import SectionDraft


class ArtifactStore:
    """Filesystem-based artifact storage."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize artifact store.
        
        Args:
            base_dir: Base directory for issues. Defaults to config.issues_dir.
        """
        if base_dir is None:
            settings = get_settings()
            base_dir = settings.issues_dir
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_issue_dir(self, newsletter_id: str) -> Path:
        """Get the directory for a specific newsletter issue."""
        issue_dir = self.base_dir / newsletter_id
        issue_dir.mkdir(parents=True, exist_ok=True)
        return issue_dir
    
    def _get_sections_dir(self, newsletter_id: str) -> Path:
        """Get the sections subdirectory."""
        sections_dir = self._get_issue_dir(newsletter_id) / "sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        return sections_dir
    
    def _get_evidence_dir(self, newsletter_id: str) -> Path:
        """Get the evidence subdirectory."""
        evidence_dir = self._get_issue_dir(newsletter_id) / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        return evidence_dir
    
    def _get_reviews_dir(self, newsletter_id: str) -> Path:
        """Get the reviews subdirectory."""
        reviews_dir = self._get_issue_dir(newsletter_id) / "reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
        return reviews_dir
    
    def write_newsletter(self, newsletter_id: str, content: str) -> str:
        """
        Write the final newsletter markdown.
        
        Returns:
            Path to the written file.
        """
        issue_dir = self._get_issue_dir(newsletter_id)
        path = issue_dir / "newsletter.md"
        path.write_text(content, encoding="utf-8")
        return str(path)
    
    def write_section(
        self,
        newsletter_id: str,
        section_id: str,
        draft: SectionDraft,
    ) -> Dict[str, str]:
        """
        Write section markdown and JSON.
        
        Returns:
            Dict with 'md' and 'json' paths.
        """
        sections_dir = self._get_sections_dir(newsletter_id)
        
        # Write markdown
        md_path = sections_dir / f"{section_id}.md"
        md_path.write_text(draft.to_markdown(), encoding="utf-8")
        
        # Write JSON
        json_path = sections_dir / f"{section_id}.json"
        json_path.write_text(
            json.dumps(draft.model_dump(), indent=2, default=str),
            encoding="utf-8"
        )
        
        return {"md": str(md_path), "json": str(json_path)}
    
    def write_evidence_pack(
        self,
        newsletter_id: str,
        section_id: str,
        evidence_pack: EvidencePack,
    ) -> str:
        """
        Write evidence pack JSON.
        
        Returns:
            Path to the written file.
        """
        evidence_dir = self._get_evidence_dir(newsletter_id)
        path = evidence_dir / f"{section_id}_pack.json"
        path.write_text(
            json.dumps(evidence_pack.model_dump(), indent=2, default=str),
            encoding="utf-8"
        )
        return str(path)
    
    def write_reviews(
        self,
        newsletter_id: str,
        section_id: str,
        reviews: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Write review round JSONs.
        
        Returns:
            List of paths to written files.
        """
        reviews_dir = self._get_reviews_dir(newsletter_id)
        paths = []
        
        for i, review in enumerate(reviews, 1):
            path = reviews_dir / f"{section_id}_review_round_{i}.json"
            path.write_text(
                json.dumps(review, indent=2, default=str),
                encoding="utf-8"
            )
            paths.append(str(path))
        
        return paths
    
    def write_metadata(
        self,
        newsletter_id: str,
        state: NewsletterState,
        workflow_state: Dict[str, Any],
    ) -> str:
        """
        Write metadata JSON.
        
        Returns:
            Path to the written file.
        """
        issue_dir = self._get_issue_dir(newsletter_id)
        path = issue_dir / "meta.json"
        
        meta = {
            "newsletter_id": newsletter_id,
            "original_prompt": state.original_prompt,
            "time_window": {
                "start": state.time_window.start.isoformat(),
                "end": state.time_window.end.isoformat(),
            },
            "voice_profile": state.voice_profile,
            "region_focus": state.region_focus,
            "style_prompt": state.style_prompt,
            "verticals_included": [v.value for v in state.verticals],
            "model_versions": state.model_versions,
            "created_at": datetime.utcnow().isoformat(),
            "total_review_rounds": workflow_state.get("current_review_round", 0),
            "editor_changes": workflow_state.get("editor_changes", []),
        }
        
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return str(path)
    
    def write_changelog(
        self,
        newsletter_id: str,
        changes: List[Dict[str, Any]],
    ) -> str:
        """
        Write or append to changelog JSON.
        
        Returns:
            Path to the written file.
        """
        issue_dir = self._get_issue_dir(newsletter_id)
        path = issue_dir / "changelog.json"
        
        existing = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        
        existing.extend(changes)
        path.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")
        return str(path)
    
    def read_newsletter(self, newsletter_id: str) -> Optional[str]:
        """Read newsletter markdown."""
        path = self._get_issue_dir(newsletter_id) / "newsletter.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None
    
    def read_section(self, newsletter_id: str, section_id: str) -> Optional[str]:
        """Read section markdown."""
        path = self._get_sections_dir(newsletter_id) / f"{section_id}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None
    
    def read_artifact(self, newsletter_id: str, artifact_path: str) -> Optional[Dict[str, Any]]:
        """Read a JSON artifact by relative path."""
        full_path = self._get_issue_dir(newsletter_id) / artifact_path
        if full_path.exists() and full_path.suffix == ".json":
            return json.loads(full_path.read_text(encoding="utf-8"))
        return None
    
    def list_issues(self) -> List[str]:
        """List all newsletter issue IDs."""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
    
    def delete_issue(self, newsletter_id: str) -> bool:
        """
        Delete a newsletter issue and all its artifacts.
        
        Returns:
            True if deleted, False if not found.
        """
        import shutil
        issue_dir = self.base_dir / newsletter_id
        if issue_dir.exists() and issue_dir.is_dir():
            shutil.rmtree(issue_dir)
            return True
        return False
