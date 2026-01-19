# File: python/app/schemas/skills.py
# Project: Tip Desktop Assistant
# Description: Skill CRUD and listing response models for GUI agent skill files.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillSummaryResponse(BaseModel):
    id: str = Field(..., description="技能唯一 ID（文件名）")
    title: str


class SkillDetailResponse(SkillSummaryResponse):
    body: str = Field("", description="技能正文，支持 Markdown")


class SkillUpsertRequest(BaseModel):
    title: str = Field(..., min_length=1, description="技能标题")
    body: str = Field("", description="技能正文内容")


class SkillRefreshResponse(BaseModel):
    count: int
