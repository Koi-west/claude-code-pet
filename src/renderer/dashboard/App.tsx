import React, { useState } from 'react';
import { ThemeProvider, ToastProvider } from '@renderer/shared/components';
import { DashboardLayout } from './components/Layout/DashboardLayout';
import { CloudCodePanel } from './components/CloudCodePanel';
import { SettingsPanel } from './components/SettingsPanel';
import { AppearancePanel } from './components/AppearancePanel';
import { ShortcutsPanel } from './components/ShortcutsPanel';
import { DesignSystemPanel } from './components/DesignSystemPanel';
import { GuiAgentPanel } from './components/GuiAgentPanel';

function DashboardContent() {
  const [activeTab, setActiveTab] = useState('cloud-code');

  const renderContent = () => {
    switch (activeTab) {
      case 'cloud-code':
        return <CloudCodePanel />;

      case 'settings':
        return <SettingsPanel />;

      case 'appearance':
        return <AppearancePanel />;

      case 'shortcuts':
        return <ShortcutsPanel />;

      case 'design-system':
        return <DesignSystemPanel />;

      case 'gui-agent':
        return <GuiAgentPanel />;

      default:
        return null;
    }
  };

  return (
    <>
      <DashboardLayout activeTab={activeTab} onTabChange={setActiveTab}>
        {renderContent()}
      </DashboardLayout>
    </>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <DashboardContent />
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;
