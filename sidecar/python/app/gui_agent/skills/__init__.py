# File: python/app/gui_agent/skills/__init__.py
# Project: Tip Desktop Assistant
# Description: Package initializer exporting skill repository types.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

"""
python.app.gui_agent.skills package initialization.
"""

from .repository import Skill, SkillSummary, SkillRepository

__all__ = ["Skill", "SkillSummary", "SkillRepository"]
