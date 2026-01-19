# Miko Desktop Pet - Project Documentation

## Overview
Miko is an Electron desktop pet with a modern chat interface and a dedicated Kohaku dashboard. It integrates with Claude Code via `@anthropic-ai/claude-agent-sdk`, supports streaming responses, tool permission prompts, and a full design system.

## Architecture
- **Main process**: Electron + TypeScript
- **Renderer**: React (pet window + dashboard)
- **Build**: Webpack for renderer, `tsc` for main process
- **Styling**: Tailwind CSS + Radix UI + Framer Motion
- **Settings**: `electron-store` with live IPC updates

## Directory Structure
```
/Users/apple/Documents/Miko-main/
├── src/
│   ├── main/
│   │   ├── index.ts
│   │   ├── ipc.ts
│   │   ├── shortcuts/
│   │   │   └── ShortcutManager.ts
│   │   ├── storage/
│   │   │   └── SettingsStore.ts
│   │   └── windows/
│   │       ├── PetWindow.ts
│   │       ├── DashboardWindow.ts
│   │       └── WindowManager.ts
│   ├── core/
│   │   ├── agent/
│   │   │   └── ClaudeAgentService.ts
│   │   ├── session/
│   │   └── streams/
│   ├── renderer/
│   │   ├── pet/
│   │   │   ├── App.tsx
│   │   │   ├── components/
│   │   │   └── hooks/
│   │   ├── dashboard/
│   │   │   ├── App.tsx
│   │   │   ├── components/
│   │   │   └── hooks/
│   │   └── shared/
│   │       ├── components/
│   │       ├── design-system/
│   │       │   ├── tokens/
│   │       │   └── themes/
│   │       └── hooks/
│   └── types/
├── public/
│   ├── pet/index.html
│   ├── dashboard/index.html
│   └── assets/
├── config/
│   ├── webpack.common.js
│   ├── webpack.main.js
│   └── webpack.renderer.js
├── tailwind.config.js
├── tsconfig.main.json
├── tsconfig.renderer.json
└── CLAUDE.md
```

## Core Features
- **Desktop pet**: Transparent, always-on-top window with animated GIF
- **Chat UI**: Streaming messages, thinking blocks, tool call visualization
- **File references**: Drag/drop, file chips, previews, recent files, `@` picker
- **Permissions**: Tool approval dialog with allow/deny/always options
- **Kohaku dashboard**: Skills, settings, appearance, shortcuts, design system
- **Theme system**: Token-based theming with live updates

## Window Management
- Pet window starts on app launch
- Dashboard toggles via shortcut (default `Shift+Control`, with fallback `CmdOrCtrl+Shift+K`)
- Settings changes propagate to windows via `settings:updated` IPC events

## Development Commands
```bash
npm install

# Production build
npm run build

# Development with watches
npm run dev

# One-shot build + run
npm run dev:simple
```

## Notes
- Renderer windows load from `dist/renderer/**` output.
- Claude settings (model, temperature, API key, system prompt) are applied to the SDK options during send.
- Themes and font size apply in real-time via CSS variables.
