# File: python/run_sidecar.py
# Project: Tip Desktop Assistant
# Description: Uvicorn entrypoint for launching the FastAPI sidecar with env-driven host and port.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import os

import uvicorn

from app.main import app as fastapi_app


def main() -> None:
    host = os.environ.get('TIP_SIDECAR_HOST', '127.0.0.1')
    port = int(os.environ.get('TIP_SIDECAR_PORT', '8787'))
    uvicorn.run(fastapi_app, host=host, port=port, reload=False, access_log=False)


if __name__ == '__main__':
    main()
