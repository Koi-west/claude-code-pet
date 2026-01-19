import React, { useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Slider,
  Switch,
} from '@renderer/shared/components';
import { colors, typography, spacing, radius, shadows } from '@renderer/shared/design-system';
import { useSettings } from '../../hooks/useSettings';
import { useToast } from '@renderer/shared/components';
import { Palette, Type, Ruler, Square, Layers, LayoutGrid } from 'lucide-react';
import { MessageList } from '@renderer/pet/components/ChatBubble/MessageList';
import { ChatInput } from '@renderer/pet/components/InputArea/ChatInput';
import { StatusIndicator } from '@renderer/pet/components/StatusIndicator';
import type { Message } from '@renderer/shared/types';
import type { FileAttachment } from '@renderer/pet/hooks/useFileAttachments';
import type { ConnectionStatusState } from '@renderer/pet/hooks/useConnectionStatus';

export function DesignSystemPanel() {
  const { settings, updateSettings } = useSettings();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState('colors');
  const [importValue, setImportValue] = useState('');

  const tabs = [
    { id: 'colors', name: 'Colors', icon: Palette },
    { id: 'typography', name: 'Typography', icon: Type },
    { id: 'spacing', name: 'Spacing', icon: Ruler },
    { id: 'radius', name: 'Radius', icon: Square },
    { id: 'shadows', name: 'Shadows', icon: Layers },
    { id: 'components', name: 'Components', icon: LayoutGrid },
  ];

  const customColors = useMemo(() => settings.customTheme?.colors || {}, [settings.customTheme]);
  const isCustomTheme = settings.theme === 'custom';
  const sampleMessages = useMemo<Message[]>(() => ([
    {
      id: 'msg-1',
      role: 'user',
      content: 'Summarize the latest changes in the project.',
      timestamp: Date.now() - 100000,
      status: 'sent',
    },
    {
      id: 'msg-2',
      role: 'assistant',
      content: 'Here is a quick summary with highlights and next steps.',
      timestamp: Date.now() - 90000,
      thinkingContent: 'Scanning changes and grouping related updates.',
      toolCalls: [
        {
          id: 'tool-1',
          name: 'Bash',
          input: { command: 'git status --short' },
          result: 'M src/renderer/dashboard/App.tsx',
        },
      ],
    },
    {
      id: 'msg-3',
      role: 'assistant',
      content: 'Drafting a response...',
      timestamp: Date.now() - 80000,
      isStreaming: true,
      thinkingContent: 'Formatting the response for clarity.',
    },
  ]), []);

  const sampleRecentFiles = useMemo<FileAttachment[]>(() => ([
    {
      id: 'file-1',
      path: '/Users/apple/Documents/Miko-main/README.md',
      name: 'README.md',
      size: 1280,
      type: 'text/markdown',
    },
  ]), []);

  const statusSamples = useMemo<ConnectionStatusState[]>(() => ([
    {
      status: 'connected',
      cliAvailable: true,
      cliPath: '/usr/local/bin/claude',
      sdkLoaded: true,
    },
    {
      status: 'disconnected',
      cliAvailable: false,
      cliPath: null,
      sdkLoaded: false,
      error: 'Claude CLI not found',
    },
    {
      status: 'error',
      cliAvailable: true,
      cliPath: '/usr/local/bin/claude',
      sdkLoaded: false,
      error: 'Failed to reach Claude Code',
    },
  ]), []);

  const handleColorChange = (family: string, shade: string, value: string) => {
    const nextCustomTheme = {
      ...settings.customTheme,
      colors: {
        ...(settings.customTheme?.colors || {}),
        [family]: {
          ...(settings.customTheme?.colors?.[family] || {}),
          [shade]: value,
        },
      },
    };

    updateSettings({
      theme: 'custom',
      customTheme: nextCustomTheme,
    });
  };

  const handleExport = async () => {
    try {
      const json = JSON.stringify(settings.customTheme || {}, null, 2);
      await navigator.clipboard.writeText(json);
      showToast({
        type: 'success',
        title: 'Theme copied',
        message: 'Custom theme JSON copied to clipboard.',
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Copy failed',
        message: 'Unable to copy JSON to clipboard.',
      });
    }
  };

  const handleImport = () => {
    try {
      const parsed = JSON.parse(importValue || '{}');
      updateSettings({
        theme: 'custom',
        customTheme: parsed,
      });
      showToast({
        type: 'success',
        title: 'Theme imported',
        message: 'Custom theme has been applied.',
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Invalid JSON',
        message: 'Please check the JSON format and try again.',
      });
    }
  };

  const renderColors = () => (
    <div className="space-y-6">
      {!isCustomTheme && (
        <div className="p-4 bg-neutral-50 border border-neutral-200 rounded-lg text-sm text-neutral-600">
          Switch to the Custom theme to edit tokens in real time.
        </div>
      )}
      <h4 className="text-lg font-semibold text-neutral-900">Color Palette (OKLCH)</h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {Object.entries(colors).map(([name, shades]) => (
          <div key={name} className="space-y-3">
            <h5 className="font-medium text-neutral-900 capitalize">{name}</h5>
            <div className="grid grid-cols-5 gap-2">
              {Object.entries(shades).map(([shade, value]) => {
                const override = customColors?.[name]?.[shade];
                const displayValue = override || value;
                return (
                  <div key={shade} className="space-y-2">
                    <div
                      className="h-12 rounded-lg border border-neutral-200"
                      style={{ backgroundColor: displayValue }}
                    />
                    <div className="text-[10px] font-mono text-neutral-600 text-center">
                      {shade}
                    </div>
                    <input
                      type="text"
                      value={displayValue}
                      onChange={(event) => handleColorChange(name, shade, event.target.value)}
                      className="w-full px-1 py-0.5 text-[10px] font-mono border border-neutral-200 rounded"
                      disabled={!isCustomTheme}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="primary" size="sm" onClick={() => updateSettings({ theme: 'custom' })}>
          Enable Custom Theme
        </Button>
        <Button variant="outline" size="sm" onClick={handleExport}>
          Export JSON
        </Button>
        <Button variant="outline" size="sm" onClick={() => updateSettings({ customTheme: {} })}>
          Reset Custom Theme
        </Button>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-neutral-700">Import Theme JSON</label>
        <textarea
          value={importValue}
          onChange={(event) => setImportValue(event.target.value)}
          className="w-full h-28 border border-neutral-200 rounded-lg p-2 text-xs font-mono"
          placeholder='{"colors": {"primary": {"500": "oklch(...)"}}}'
        />
        <Button variant="outline" size="sm" onClick={handleImport}>
          Apply Import
        </Button>
      </div>
    </div>
  );

  const renderTypography = () => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-neutral-900">Typography Scale</h4>
      <div className="space-y-6">
        <div>
          <h5 className="font-medium text-neutral-900 mb-2">Font Families</h5>
          <div className="space-y-2 text-sm text-neutral-600">
            <div>Sans: {typography.fontFamily.sans}</div>
            <div>Mono: {typography.fontFamily.mono}</div>
          </div>
        </div>

        <div>
          <h5 className="font-medium text-neutral-900 mb-2">Scale</h5>
          <div className="space-y-3">
            {Object.entries(typography.fontSize).map(([name, size]) => (
              <div key={name} className="border-b border-neutral-200 pb-3">
                <div
                  className="text-neutral-800"
                  style={{
                    fontSize: size,
                    fontWeight: typography.fontWeight.medium,
                    lineHeight: typography.lineHeight.normal,
                  }}
                >
                  The quick brown fox jumps over the lazy dog
                </div>
                <div className="text-xs text-neutral-500 font-mono">
                  {name}: {size}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderSpacing = () => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-neutral-900">Spacing System (4px Grid)</h4>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(spacing).map(([name, value]) => (
          <div key={name} className="space-y-2">
            <div
              className="h-8 rounded-lg bg-neutral-100 flex items-center justify-center"
              style={{ height: value }}
            />
            <div className="text-xs font-mono text-neutral-600 text-center">
              {name}: {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderRadius = () => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-neutral-900">Border Radius</h4>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Object.entries(radius).map(([name, value]) => (
          <div key={name} className="space-y-2">
            <div
              className="h-12 bg-primary-500 rounded"
              style={{ borderRadius: value }}
            />
            <div className="text-xs font-mono text-neutral-600 text-center">
              {name}: {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderShadows = () => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-neutral-900">Shadow Elevations</h4>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(shadows).map(([name, value]) => (
          <div key={name} className="space-y-2">
            <div
              className="h-12 bg-white rounded-lg flex items-center justify-center"
              style={{ boxShadow: value }}
            />
            <div className="text-xs font-mono text-neutral-600 text-center">
              {name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderComponents = () => (
    <div className="space-y-6">
      <h4 className="text-lg font-semibold text-neutral-900">Component Showcase</h4>

      <Card variant="outline">
        <CardHeader>
          <CardTitle>Core Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button variant="primary">Primary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Input placeholder="Input" />
            <Input placeholder="Search" />
          </div>

          <div className="flex items-center gap-4">
            <Switch checked={true} onCheckedChange={() => {}} />
            <Slider value={40} min={0} max={100} onChange={() => {}} />
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="primary">Primary</Badge>
            <Badge variant="success">Success</Badge>
            <Badge variant="warning">Warning</Badge>
            <Badge variant="error">Error</Badge>
            <Badge variant="neutral">Neutral</Badge>
          </div>
        </CardContent>
      </Card>

      <Card variant="outline">
        <CardHeader>
          <CardTitle>Chat UI</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border border-neutral-200 rounded-lg overflow-hidden bg-white flex flex-col h-72">
            <MessageList messages={sampleMessages} />
            <ChatInput
              onSend={(_content) => {}}
              onAttach={() => {}}
              onRecentSelect={(_file) => {}}
              recentFiles={sampleRecentFiles}
              isStreaming={false}
              onInterrupt={() => {}}
            />
          </div>
        </CardContent>
      </Card>

      <Card variant="outline">
        <CardHeader>
          <CardTitle>Status Indicators</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-6">
          {statusSamples.map((status) => (
            <div key={status.status} className="rounded-lg border border-neutral-200 px-3 py-2 bg-white">
              <StatusIndicator status={status} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'colors':
        return renderColors();
      case 'typography':
        return renderTypography();
      case 'spacing':
        return renderSpacing();
      case 'radius':
        return renderRadius();
      case 'shadows':
        return renderShadows();
      case 'components':
        return renderComponents();
      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-neutral-900 mb-2">Design System</h3>
        <p className="text-neutral-600 text-sm">
          View and customize the design tokens used throughout the application.
        </p>
      </div>

      <div className="bg-neutral-50 rounded-lg p-6">
        <div className="flex gap-2 mb-6 flex-wrap">
          {tabs.map((tab) => (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2"
            >
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </Button>
          ))}
        </div>

        {renderContent()}
      </div>
    </div>
  );
}
