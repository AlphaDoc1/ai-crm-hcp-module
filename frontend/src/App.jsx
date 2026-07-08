// src/App.jsx
import React from 'react';
import LogInteractionForm from './components/LogInteractionForm';
import AIChatPanel from './components/AIChatPanel';

export default function App() {
  return (
    <div className="app-root">
      {/* Header */}
      <header className="app-header">
        <div className="app-header-logo">
          <div className="app-header-logo-icon">⚕</div>
          <div>
            <span className="app-header-title">AI-CRM</span>
            <span className="app-header-subtitle">HCP Interaction Module</span>
          </div>
        </div>
        <div className="app-header-badge">✦ LangGraph · gpt-oss-20b via Groq</div>
      </header>

      {/* Two-panel main layout */}
      <main className="main-layout">
        <LogInteractionForm />
        <AIChatPanel />
      </main>
    </div>
  );
}
