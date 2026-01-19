import React from 'react';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  children: React.ReactNode;
}

export function DashboardLayout({ activeTab, onTabChange, children }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen bg-neutral-50">
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}