# Claude Code Desktop Pet Refactoring Plan

## Phase 1: Project Setup & Migration

### 1.1 Initialize TypeScript Project
- [ ] Create new TypeScript configuration
- [ ] Set up build tools (Vite + Electron Forge)
- [ ] Install dependencies:
  - @anthropic-ai/claude-agent-sdk
  - electron, react, react-dom
  - @types packages
  - webpack/vite for bundling

### 1.2 Migrate Project Structure
- [ ] Create `src/` directory structure
- [ ] Move existing HTML/CSS to React components
- [ ] Convert main.js to TypeScript
- [ ] Update package.json scripts

### 1.3 Preserve Existing Features
- [ ] Extract pet window configuration
- [ ] Maintain GIF animation setup
- [ ] Preserve drag functionality
- [ ] Keep window management (always-on-top)

## Phase 2: Claude Integration Layer

### 2.1 Implementation Strategy
Based on claudian patterns, implement Claude Code integration using:
- Claude Agent SDK for process management
- Persistent query pattern for low latency
- JSONL protocol for communication
- Stream processing with error handling

### 2.2 Core Agent Service (`src/core/agent/ClaudeAgentService.ts`)
```typescript
class ClaudeAgentService {
  private agent: any; // SDK agent instance
  private persistentQuery: any;
  private messageChannel: MessageChannel;
  private sessionManager: SessionManager;

  async initialize()
  async sendMessage(content: string)
  async handleStreamResponse()
  async resolveFileReferences(content: string)
}
```

### 2.3 Message Channel (`src/core/agent/MessageChannel.ts`)
- Queue-based message handling
- Text merging for continuous streams
- Attachment handling for file references
- Overflow management

### 2.4 Session Management (`src/core/session/SessionManager.ts`)
- Session lifecycle tracking
- JSONL history persistence
- Session mismatch detection
- Context recovery on failure

### 2.5 Stream Controller (`src/core/streams/StreamController.ts`)
- Real-time message processing
- Thinking block rendering
- Tool call visualization
- Error state handling

## Phase 3: UI Components

### 3.1 Main Pet Component
```typescript
interface PetProps {
  position: { x: number; y: number }
  onDrag: (pos: Position) => void
  onClick: () => void
}
```

### 3.2 Chat Dialog Component
```typescript
interface ChatDialogProps {
  visible: boolean
  messages: Message[]
  onSendMessage: (text: string) => void
  onInterrupt: () => void
  streaming: boolean
}
```

### 3.3 Message Types
- Text messages (user/assistant)
- Thinking blocks (collapsible)
- Tool use/result pairs
- File reference chips
- Error messages

### 3.4 Input Components
- Message input with @ file reference support
- Session selector
- Interrupt button during streaming
- Connection status indicator

## Phase 4: Feature Implementation

### 4.1 File References (@ syntax)
```typescript
// Implementation approach from claudian:
const FILE_REFERENCE = /(^|[^\w])@(?:"([^"]+)"|'([^']+)'|([^\s]+\.\w+))/g;

async resolveFileReferences(content: string): Promise<string> {
  // Replace @file references with file contents
  // Show file selection dialog
  // Extract content based on selection
}
```

### 4.2 Session Management Features
- [ ] Session creation (Ctrl/Cmd+N)
- [ ] Session switching dropdown
- [ ] Session history list
- [ ] Session search/filter

### 4.3 Streaming Output (Typewriter Effect)
```typescript
class StreamProcessor {
  private buffer: string[] = [];
  private interval: NodeJS.Timeout;
  private speed: number = 30; // ms per character

  addText(text: string)
  start(callback: (char: string) => void)
  stop()
}
```

### 4.4 Interrupt Handling
- [ ] Ctrl+C detection
- [ ] UI interrupt button
- [ ] Abort controller integration
- [ ] Graceful response termination

## Phase 5: Testing & Polish

### 5.1 Unit Tests
- [ ] Agent service tests
- [ ] Session manager tests
- [ ] Stream controller tests
- [ ] File reference resolver tests

### 5.2 Integration Tests
- [ ] Full conversation flow
- [ ] Session persistence
- [ ] File reference handling
- [ ] Error recovery scenarios

### 5.3 Platform Testing
- [ ] macOS functionality (primary)
- [ ] Windows compatibility
- [ ] Linux support (if needed)

## Module Implementation Order

### Module 1: Core Infrastructure
1. Set up TypeScript project structure
2. Migrate Electron main process
3. Create basic window management
4. Test existing pet functionality

### Module 2: Claude Agent Integration
1. Install Claude Agent SDK
2. Create AgentService wrapper
3. Implement basic message sending
4. Handle simple text responses

### Module 3: Streaming & UI
1. Implement StreamController
2. Create typewriter effect
3. Build message components
4. Integrate with React UI

### Module 4: Advanced Features
1. File reference resolver
2. Session management
3. History persistence
4. Error handling

### Module 5: Polish & Testing
1. UI refinements
2. Performance optimization
3. Cross-platform testing
4. Documentation updates

## Critical Implementation Files

1. **src/main/index.ts** - Electron main process entry
2. **src/core/agent/ClaudeAgentService.ts** - Claude integration
3. **src/core/streams/StreamController.ts** - Real-time output
4. **src/core/session/SessionManager.ts** - Conversation management
5. **src/renderer/components/ChatDialog.tsx** - Main UI component

## Testing Strategy

For each completed module:
1. Run `npm run dev` to test in development
2. Verify pet animation and dragging works
3. Test connections to Claude Code
4. Check streaming output appears correctly
5. Validate file references (@ syntax)
6. Confirm session persistence

## Architecture Diagram

```
┌─────────────────────────────────┐
│      Electron Main Process     │
│  ┌───────────────────────────┐  │
│  │   Electron Window Mgmt    │  │
│  └───────────────────────────┘  │
└─────────────┬───────────────────┘
              │ IPC
┌─────────────┴───────────────────┐
│    Renderer Process (React)    │
│  ┌───────────────────────────┐  │
│  │   Pet Component           │  │
│  │   Chat Dialog Component   │  │
│  └─────────────┬─────────────┘  │
└───────────────┼─────────────────┘
                │
┌───────────────┼─────────────────┐
│  Claude Agent SDK Integration  │
│  ┌─────────────┴─────────────┐  │
│  │   Persistent Query        │  │
│  │   Message Channel         │  │
│  │   Stream Controller       │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```