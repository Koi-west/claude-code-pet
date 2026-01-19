# File: python/app/gui_agent/__init__.py
# Project: Tip Desktop Assistant
# Description: Package exports for GUI agent integration (run_prompt, build_default_args).

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

"""GUI agent integration for Tip sidecar."""

from .runner import run_prompt, build_default_args

__all__ = ["run_prompt", "build_default_args"]
