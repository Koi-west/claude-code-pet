# File: python/app/gui_agent/qwen_skills.py
# Project: Tip Desktop Assistant
# Description: SkillManager that caches skill catalog, extracts <skill> requests, and formats replies.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import re
from typing import List, Optional

from .skills import Skill, SkillRepository, SkillSummary


class SkillManager:
    """Handle skill catalog caching and lookups for the Qwen agent."""

    def __init__(
        self,
        repo: Optional[SkillRepository],
    ) -> None:
        self._repo = repo
        self._catalog: Optional[List[SkillSummary]] = None

    def build_catalog_section(self) -> str:
        summaries = self._get_catalog()
        if not summaries:
            return "(no skills available)"

        lines = []
        for summary in summaries:
            lines.append(f"- {summary.title}")
        return "\n".join(lines)

    def extract_requests(self, response: str) -> List[str]:
        if not response:
            return []
        pattern = re.compile(r"<skill>(.*?)</skill>", re.IGNORECASE | re.DOTALL)
        requests: List[str] = []
        for match in pattern.finditer(response):
            ref = match.group(1).strip()
            if ref:
                requests.append(ref)
        return requests

    def lookup(self, reference: str) -> Optional[Skill]:
        if not self._repo:
            return None
        ref = (reference or "").strip()
        if not ref:
            return None
        try:
            return self._repo.get(ref)
        except KeyError:
            return self._repo.get_by_title(ref)

    def build_skill_reply(self, reference: str) -> tuple[str, bool]:
        skill = self.lookup(reference)
        if skill:
            return self.format_skill_message(skill), True
        return (
            f'Skill "{reference}" is not available. Continue the task without it.',
            False,
        )

    @staticmethod
    def format_skill_message(skill: Skill) -> str:
        body = skill.body.strip() or "（技能暂无详细步骤）"
        return (
            f'Here is the stored skill "{skill.title}". '
            "Treat the following steps as a reliable example:\n"
            f"{body}"
        )

    def reset_cache(self) -> None:
        """Clear cached catalog data. Call when agent resets."""
        self._catalog = None

    def _get_catalog(self) -> List[SkillSummary]:
        if self._catalog is None and self._repo:
            try:
                self._catalog = self._repo.list_titles()
            except Exception:
                self._catalog = []
        return self._catalog or []
