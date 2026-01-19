import React from 'react';
import { Button } from '@renderer/shared/components';
import { Cloud, Settings, Palette, Keyboard, Code, Bot } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const navItems = [
    { id: 'cloud-code', name: 'Cloud Code', icon: Cloud, description: 'Sync Claude Code settings' },
    { id: 'settings', name: 'Settings', icon: Settings, description: 'Configure Claude settings' },
    { id: 'gui-agent', name: 'GUI Agent', icon: Bot, description: 'Configure screen automation' },
    { id: 'appearance', name: 'Appearance', icon: Palette, description: 'Customize theme and UI' },
    { id: 'shortcuts', name: 'Shortcuts', icon: Keyboard, description: 'Manage keyboard shortcuts' },
    { id: 'design-system', name: 'Design System', icon: Code, description: 'View design tokens' },
  ];

  return (
    <aside className="w-64 bg-white border-r border-neutral-200 flex flex-col">
      {/* Logo/Title */}
      <div className="p-6 border-b border-neutral-200">
        <h1 className="text-2xl font-bold text-neutral-900">Kohaku</h1>
        <p className="text-sm text-neutral-500 mt-1">Dashboard</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Button
              key={item.id}
              variant={activeTab === item.id ? 'primary' : 'ghost'}
              size="base"
              onClick={() => onTabChange(item.id)}
              className="w-full justify-start text-left"
            >
              <Icon className="w-5 h-5 mr-3 flex-shrink-0" />
              <div className="flex-1">
                <span className="font-medium">{item.name}</span>
                <p className="text-xs text-neutral-500 mt-0.5">{item.description}</p>
              </div>
            </Button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-neutral-200">
        <div className="text-xs text-neutral-500">
          <p>Miko Desktop Pet</p>
          <p>Version 2.0.0</p>
        </div>
      </div>
    </aside>
  );
}
