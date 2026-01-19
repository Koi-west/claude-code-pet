# File: python/app/services/text_selection.py
# Project: Tip Desktop Assistant
# Description: macOS-only helper that simulates copy and reads NSPasteboard to capture selected text safely.

# Copyright (C) 2025 Tencent. All rights reserved.
# License: Licensed under the License Terms of Youtu-Tip (see license at repository root).
# Warranty: Provided on an "AS IS" basis, without warranties or conditions of any kind.
# Modifications must retain this notice.

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import structlog
from pynput.keyboard import Controller, Key

try:  # pyobjc is only available on macOS
    from AppKit import NSPasteboard, NSPasteboardItem, NSPasteboardTypeString
    from Foundation import NSData
except Exception:  # pragma: no cover - fallback when AppKit is unavailable
    NSPasteboard = None
    NSPasteboardItem = None
    NSPasteboardTypeString = 'public.utf8-plain-text'
    NSData = None

logger = structlog.get_logger(__name__)


@dataclass
class PasteboardItemSnapshot:
    payloads: List[Tuple[str, bytes]]


class TextSelectionService:
    def __init__(
        self,
        poll_interval: float = 0.03,
        timeout_seconds: float = 0.5,
        copy_delay: float = 0.04,
    ) -> None:
        self._poll_interval = poll_interval
        self._timeout = timeout_seconds
        self._copy_delay = copy_delay
        self._lock = asyncio.Lock()
        self._keyboard = Controller()
        self._available = sys.platform == 'darwin' and NSPasteboard is not None and NSPasteboardItem is not None

    async def capture_selected_text(self) -> Optional[str]:
        if not self._available:
            logger.debug('text_selection.unavailable', reason='platform or AppKit unsupported')
            return None
        async with self._lock:
            pasteboard = NSPasteboard.generalPasteboard()  # type: ignore[union-attr]
            snapshot = self._snapshot_items(pasteboard)
            baseline = pasteboard.changeCount()
            text_result: Optional[str] = None
            try:
                self._simulate_copy_shortcut()
                await asyncio.sleep(self._copy_delay)
                text_result = await self._wait_for_text(pasteboard, baseline)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning('text_selection.capture_failed', error=str(exc))
            finally:
                self._restore_snapshot(pasteboard, snapshot)
            if text_result:
                logger.debug('text_selection.captured', length=len(text_result))
            return text_result

    def _simulate_copy_shortcut(self) -> None:
        pressed: List[object] = []
        try:
            self._keyboard.press(Key.cmd)
            pressed.append(Key.cmd)
            self._keyboard.press('c')
            pressed.append('c')
            self._keyboard.release('c')
            pressed.remove('c')
            self._keyboard.release(Key.cmd)
            pressed.remove(Key.cmd)
        finally:
            for key in reversed(pressed):
                try:
                    self._keyboard.release(key)
                except Exception:  # pragma: no cover - ensure no stuck modifier
                    continue

    async def _wait_for_text(self, pasteboard, baseline: int) -> Optional[str]:  # type: ignore[no-untyped-def]
        deadline = asyncio.get_event_loop().time() + self._timeout
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(self._poll_interval)
            if pasteboard.changeCount() == baseline:
                continue
            text = pasteboard.stringForType_(self._string_type())  # type: ignore[attr-defined]
            if text:
                value = str(text)
                if value.strip():
                    return value
            # change detected but no plain text; continue polling
        return None

    def _snapshot_items(self, pasteboard) -> Sequence[PasteboardItemSnapshot]:  # type: ignore[no-untyped-def]
        items = pasteboard.pasteboardItems() or []
        snapshots: List[PasteboardItemSnapshot] = []
        for item in items:
            payloads: List[Tuple[str, bytes]] = []
            for type_identifier in item.types() or []:
                data = item.dataForType_(type_identifier)
                if data:
                    payloads.append((str(type_identifier), bytes(data)))
            snapshots.append(PasteboardItemSnapshot(payloads=payloads))
        return snapshots

    def _restore_snapshot(
        self,
        pasteboard,
        snapshots: Sequence[PasteboardItemSnapshot],
    ) -> None:  # type: ignore[no-untyped-def]
        try:
            pasteboard.clearContents()
            if not snapshots or NSData is None:
                return
            restored_items = []
            for snapshot in snapshots:
                item = NSPasteboardItem.alloc().init()  # type: ignore[union-attr]
                for type_identifier, payload in snapshot.payloads:
                    ns_data = NSData.dataWithBytes_length_(payload, len(payload))  # type: ignore[union-attr]
                    item.setData_forType_(ns_data, type_identifier)
                restored_items.append(item)
            if restored_items:
                pasteboard.writeObjects_(restored_items)
        except Exception as exc:  # pragma: no cover - restoration best-effort
            logger.warning('text_selection.restore_failed', error=str(exc))

    def _string_type(self) -> str:
        if isinstance(NSPasteboardTypeString, str):
            return NSPasteboardTypeString
        return str(NSPasteboardTypeString)  # type: ignore[arg-type]
