# File: python/app/api/routes_skills.py
# Project: Tip Desktop Assistant
# Description: Skill CRUD endpoints backed by the SkillRepository.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.deps import get_skill_repository
from ..gui_agent.skills import SkillRepository
from ..schemas.skills import (
    SkillDetailResponse,
    SkillRefreshResponse,
    SkillSummaryResponse,
    SkillUpsertRequest,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/", response_model=list[SkillSummaryResponse])
def list_skills(
    repo: SkillRepository = Depends(get_skill_repository),
) -> list[SkillSummaryResponse]:
    summaries = repo.list_titles()
    return [SkillSummaryResponse(id=item.id, title=item.title) for item in summaries]


@router.get("/{skill_id}", response_model=SkillDetailResponse)
def get_skill(
    skill_id: str,
    repo: SkillRepository = Depends(get_skill_repository),
) -> SkillDetailResponse:
    try:
        skill = repo.get(skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc
    return SkillDetailResponse(id=skill.id, title=skill.title, body=skill.body)


@router.post("/", response_model=SkillDetailResponse)
def create_skill(
    payload: SkillUpsertRequest,
    repo: SkillRepository = Depends(get_skill_repository),
) -> SkillDetailResponse:
    skill = repo.upsert(title=payload.title, body=payload.body)
    return SkillDetailResponse(id=skill.id, title=skill.title, body=skill.body)


@router.put("/{skill_id}", response_model=SkillDetailResponse)
def update_skill(
    skill_id: str,
    payload: SkillUpsertRequest,
    repo: SkillRepository = Depends(get_skill_repository),
) -> SkillDetailResponse:
    try:
        repo.get(skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc
    skill = repo.upsert(title=payload.title, body=payload.body, skill_id=skill_id)
    return SkillDetailResponse(id=skill.id, title=skill.title, body=skill.body)


@router.delete("/{skill_id}")
def delete_skill(skill_id: str, repo: SkillRepository = Depends(get_skill_repository)) -> dict:
    try:
        repo.delete(skill_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc
    return {"status": "deleted", "id": skill_id}


@router.post("/refresh", response_model=SkillRefreshResponse)
def refresh_skills(repo: SkillRepository = Depends(get_skill_repository)) -> SkillRefreshResponse:
    repo.refresh()
    count = len(repo.list_titles())
    return SkillRefreshResponse(count=count)
