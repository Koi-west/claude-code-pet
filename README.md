# Miko Desktop Pet

Miko is an Electron desktop pet with a modern chat UI, streaming Claude Code responses, and a full Kohaku dashboard for settings, skills, and design tokens.

## Requirements
- Node.js 18+
- npm
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

## Setup
```bash
npm install
```

## Development
```bash
npm run dev
```

## GUI Agent (Screen Automation)
The GUI Agent sidecar lives in `sidecar/python` and is managed from the dashboard.

- Open the dashboard and go to **GUI Agent** to configure the sidecar URL and VLM settings.
- Enable **Auto-start** to launch the sidecar when Miko starts, or start it manually in the panel.
- Sidecar dependencies are listed in `sidecar/python/pyproject.toml`.

## Build and Run
```bash
npm run build
npm start
```

## Shortcuts
- Dashboard toggle: `Shift+Control` (fallback: `CmdOrCtrl+Shift+K`)

## Notes
- Renderer builds are written to `dist/renderer`.
- Settings are persisted via `electron-store` and broadcast to both windows.
