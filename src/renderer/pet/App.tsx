import React, { useState } from 'react';
import { ipcRenderer } from 'electron';
import { ThemeProvider } from '@renderer/shared/components';
import { MessageList } from './components/ChatBubble/MessageList';
import { ChatInput } from './components/InputArea/ChatInput';
import { FileChips } from './components/InputArea/FileChips';
import { FileDropZone } from './components/InputArea/FileDropZone';
import { PermissionDialog } from './components/PermissionDialog';
import { StatusIndicator } from './components/StatusIndicator';
import { PetImage } from './components/PetImage';
import { useChatMessages } from './hooks/useChatMessages';
import { useFileAttachments } from './hooks/useFileAttachments';
import { usePermissionRequests } from './hooks/usePermissionRequests';
import { useConnectionStatus } from './hooks/useConnectionStatus';
import { IPC_CHANNELS } from '@types';

function App() {
  const { messages, isStreaming, sendMessage, interrupt, queuedCount } = useChatMessages();
  const {
    attachedFiles,
    recentFiles,
    addFiles,
    addFileFromDialog,
    attachRecentFile,
    removeFile,
    clearFiles,
  } = useFileAttachments();
  const { request, respond } = usePermissionRequests();
  const connectionStatus = useConnectionStatus();
  const [isChatVisible, setIsChatVisible] = useState(true);

  const handleSendMessage = async (content: string) => {
    const references = attachedFiles.map((file) => `@"${file.path}"`).join(' ');
    const withFiles = references ? `${content}\n${references}` : content;

    await sendMessage(withFiles.trim());
    clearFiles();
  };

  return (
    <ThemeProvider>
      <FileDropZone onFilesDrop={addFiles}>
        <div className="w-full h-full flex items-center justify-start p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center drag-region">
              <PetImage onToggleChat={() => setIsChatVisible((prev) => !prev)} />
            </div>

            {isChatVisible && (
              <div className="flex flex-col gap-3 no-drag">
                <div className="w-[340px] h-[260px] bg-white/95 rounded-2xl shadow-lg border border-neutral-200 backdrop-blur-sm flex flex-col overflow-hidden no-drag">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-200">
                    <div>
                      <div className="text-xs font-semibold text-neutral-900">Kohaku</div>
                      <div className="text-[10px] text-neutral-500">Desktop companion</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {queuedCount > 0 && (
                        <span className="text-[10px] text-neutral-500">Queued {queuedCount}</span>
                      )}
                      <StatusIndicator status={connectionStatus} />
                      {isStreaming && (
                        <span
                          className="w-2.5 h-2.5 bg-error-500 rounded-sm animate-pulse"
                          title="Processing"
                        />
                      )}
                      <button
                        onClick={() => ipcRenderer.send(IPC_CHANNELS.TOGGLE_WINDOW, 'dashboard')}
                        className="text-[10px] text-primary-600 hover:text-primary-700 transition-colors"
                        title="Toggle dashboard"
                      >
                        Dashboard
                      </button>
                    </div>
                  </div>

                  <MessageList messages={messages} />

                  <FileChips files={attachedFiles} onRemove={removeFile} />

                  <ChatInput
                    onSend={handleSendMessage}
                    onAttach={addFileFromDialog}
                    onRecentSelect={attachRecentFile}
                    recentFiles={recentFiles}
                    isStreaming={isStreaming}
                    onInterrupt={interrupt}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </FileDropZone>

      <PermissionDialog request={request} onDecision={respond} />
    </ThemeProvider>
  );
}

export default App;
