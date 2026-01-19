# File: python/app/gui_agent/skills/repository.py
# Project: Tip Desktop Assistant
# Description: SkillRepository for reading/writing markdown skills with caching, slugging, and CRUD helpers.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Skill:
    """完整的技能定义。"""

    id: str
    title: str
    body: str
    path: Path


@dataclass(frozen=True)
class SkillSummary:
    """只包含标题信息，供 GUI Agent 首轮注入使用。"""

    id: str
    title: str


class SkillRepository:
    """
    负责从指定目录读取/缓存技能 Markdown，并提供基础 CRUD。
    读取格式规则：
      * 以第一条非空行作为标题，自动去掉开头的 # 或空白
      * 其余内容视为 body，可为空
    """

    def __init__(self, skills_dir: Path | str) -> None:
        self._skills_dir = Path(skills_dir).expanduser().resolve()
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._skills: Dict[str, Skill] = {}
        self.refresh()

    # ----------------------------
    # Public API
    # ----------------------------
    def refresh(self) -> None:
        """重新扫描目录，更新缓存。"""
        with self._lock:
            skills: Dict[str, Skill] = {}
            for path in sorted(self._skills_dir.glob("*.md")):
                skill = self._load_skill(path)
                if skill:
                    skills[skill.id] = skill
            self._skills = skills

    def list_titles(self) -> List[SkillSummary]:
        """返回全部技能的标题。"""
        with self._lock:
            return [SkillSummary(id=s.id, title=s.title) for s in self._skills.values()]

    def get(self, skill_id: str) -> Skill:
        """根据 id 获取技能，找不到则抛出 KeyError。"""
        with self._lock:
            if skill_id not in self._skills:
                raise KeyError(skill_id)
            return self._skills[skill_id]

    def get_by_title(self, title: str) -> Optional[Skill]:
        normalized = title.strip().lower()
        with self._lock:
            for skill in self._skills.values():
                if skill.title.strip().lower() == normalized:
                    return skill
        return None

    def upsert(self, *, title: str, body: str, skill_id: Optional[str] = None) -> Skill:
        """
        创建或更新技能。
        如果指定 skill_id 且存在，则覆盖文件；否则自动根据标题生成唯一文件名。
        """
        title = title.strip()
        body = body.strip("\n")
        if not title:
            raise ValueError("title is required")

        with self._lock:
            if skill_id:
                filename = f"{skill_id}.md"
                path = self._skills_dir / filename
            else:
                slug = self._slugify(title)
                path = self._unique_path(slug)
                skill_id = path.stem

            content = self._compose_file(title, body)
            path.write_text(content, encoding="utf-8")

            skill = Skill(
                id=skill_id,
                title=title,
                body=body.strip(),
                path=path,
            )
            self._skills[skill.id] = skill
            return skill

    def delete(self, skill_id: str) -> None:
        with self._lock:
            skill = self._skills.get(skill_id)
            if not skill:
                raise KeyError(skill_id)
            if skill.path.exists():
                skill.path.unlink()
            self._skills.pop(skill_id, None)

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _load_skill(self, path: Path) -> Optional[Skill]:
        try:
            data = path.read_text(encoding="utf-8")
        except OSError:
            return None
        title, body = self._parse_markdown(data, fallback_title=path.stem)
        return Skill(id=path.stem, title=title, body=body, path=path)

    @staticmethod
    def _parse_markdown(text: str, *, fallback_title: str) -> tuple[str, str]:
        lines = text.splitlines()
        title = None
        body_lines: Iterable[str] = ()
        for idx, raw in enumerate(lines):
            stripped = raw.strip()
            if stripped:
                title = stripped.lstrip("# ").strip() or fallback_title
                body_lines = lines[idx + 1 :]
                break

        if title is None:
            title = fallback_title
            body_lines = lines

        body = "\n".join(body_lines).strip()
        return title, body

    def _unique_path(self, slug: str) -> Path:
        base = slug or "skill"
        path = self._skills_dir / f"{base}.md"
        counter = 1
        while path.exists():
            path = self._skills_dir / f"{base}-{counter}.md"
            counter += 1
        return path

    @staticmethod
    def _compose_file(title: str, body: str) -> str:
        if body:
            return f"# {title}\n\n{body.rstrip()}\n"
        return f"# {title}\n"

    @staticmethod
    def _slugify(text: str) -> str:
        slug = text.strip().lower()
        # Keep unicode letters/digits (e.g. Chinese) so filenames remain identifiable.
        slug = re.sub(r"[^\w-]+", "-", slug, flags=re.UNICODE)
        slug = re.sub(r"-{2,}", "-", slug)
        slug = slug.strip("-_")
        return slug or "skill"
