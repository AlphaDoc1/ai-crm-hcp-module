// src/components/AIChatPanel.jsx
// RIGHT PANEL — AI Assistant chat powered by LangGraph
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useDispatch, useSelector } from 'react-redux';
import {
  sendMessage,
  addUserMessage,
  clearChat,
  selectMessages,
  selectChatStatus,
  selectLastToolUsed,
} from '../features/chat/chatSlice';

// ── Tool badge colors ─────────────────────────────────────────────────────────
const TOOL_COLORS = {
  log_interaction: { bg: '#ecfdf5', color: '#065f46', label: '📝 log_interaction' },
  edit_interaction: { bg: '#eff6ff', color: '#1e40af', label: '✏️ edit_interaction' },
  search_hcp: { bg: '#fdf4ff', color: '#6b21a8', label: '🔍 search_hcp' },
  suggest_followups: { bg: '#fff7ed', color: '#9a3412', label: '💡 suggest_followups' },
  summarize_interaction: { bg: '#f0fdf4', color: '#14532d', label: '📊 summarize_interaction' },
};

// ── Single chat message ───────────────────────────────────────────────────────
function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const toolStyle = message.toolUsed ? TOOL_COLORS[message.toolUsed] : null;

  const formatTime = (ts) => {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
      {/* Tool badge */}
      {message.toolUsed && toolStyle && (
        <div
          className="chat-tool-badge"
          style={{ background: toolStyle.bg, color: toolStyle.color, marginBottom: '4px' }}
        >
          {toolStyle.label}
        </div>
      )}

      <div className={`chat-bubble ${message.role}${message.isError ? ' error' : ''}`}>
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        ) : (
          <div className="chat-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>

      <div className="chat-timestamp">{formatTime(message.timestamp)}</div>
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="chat-typing">
      <div
        style={{
          background: 'var(--color-surface-2)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md) var(--radius-md) var(--radius-md) 4px',
          padding: '10px 14px',
          display: 'flex',
          gap: '4px',
          alignItems: 'center',
        }}
      >
        <div className="chat-typing-dot" />
        <div className="chat-typing-dot" />
        <div className="chat-typing-dot" />
      </div>
    </div>
  );
}

// ── Quick action buttons ──────────────────────────────────────────────────────
const QUICK_PROMPTS = [
  { label: '🔍 Search HCP', text: 'Search for Dr. Sharma' },
  { label: '📋 Log Interaction', text: 'Met Dr. Mehta at Fortis today, discussed CardioShield dosing for AF patients, positive sentiment, shared the DDI reference card' },
  { label: '💡 Suggest Follow-ups', text: 'Suggest follow-ups for interaction 1' },
  { label: '📊 Summarize', text: 'Summarize this: Met Dr. Iyer at NIMHANS, reviewed NeuroCalm XR pediatric data, he was interested in the revised SmPC, shared patient info leaflet' },
];

// ── Main Chat Panel ───────────────────────────────────────────────────────────
export default function AIChatPanel() {
  const dispatch = useDispatch();
  const messages = useSelector(selectMessages);
  const chatStatus = useSelector(selectChatStatus);
  const lastToolUsed = useSelector(selectLastToolUsed);

  const [inputValue, setInputValue] = useState('');
  const chatContainerRef = useRef(null);
  const inputRef = useRef(null);
  const isLoading = chatStatus === 'loading';

  // Auto-scroll inside the chat container to avoid window scrolling
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // Build conversation history for context
  const getHistory = () =>
    messages
      .filter((m) => m.id !== 'welcome')
      .slice(-10) // last 10 messages for context window
      .map((m) => ({ role: m.role, content: m.content }));

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isLoading) return;

    dispatch(addUserMessage(text));
    setInputValue('');
    dispatch(sendMessage({ message: text, history: getHistory() }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickPrompt = (text) => {
    if (isLoading) return;
    dispatch(addUserMessage(text));
    dispatch(sendMessage({ message: text, history: getHistory() }));
  };

  return (
    <div className="panel-card" style={{ height: 'calc(100vh - 90px)', minHeight: '600px' }}>
      {/* Panel header */}
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div className="panel-header-title">AI Assistant</div>
            <div className="panel-header-name" style={{ fontSize: '16px' }}>
              Log interaction via chat
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {lastToolUsed && (
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  background: 'var(--color-success-light)',
                  color: 'var(--color-success)',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  border: '1px solid #6ee7b7',
                }}
              >
                Last: {lastToolUsed}
              </span>
            )}
            <span
              className="ai-badge"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #2563eb)' }}
            >
              ✦ LangGraph
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => dispatch(clearChat())}
              title="Clear conversation"
              id="clear-chat-btn"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Quick action prompts */}
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px' }}>
          {QUICK_PROMPTS.map((qp) => (
            <button
              key={qp.label}
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '11px', padding: '4px 10px' }}
              onClick={() => handleQuickPrompt(qp.text)}
              disabled={isLoading}
            >
              {qp.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages area */}
      <div
        ref={chatContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          background: 'var(--color-surface)',
        }}
      >
        {/* Guidance placeholder if only welcome message */}
        {messages.length === 1 && (
          <div
            style={{
              textAlign: 'center',
              padding: '24px 20px',
              color: 'var(--color-text-muted)',
              fontSize: '13px',
              background: 'var(--color-surface-2)',
              borderRadius: 'var(--radius-md)',
              border: '1.5px dashed var(--color-border)',
              margin: '8px 0',
            }}
          >
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>🤖</div>
            <div style={{ fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '6px' }}>
              Log interaction details here
            </div>
            <div>
              e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure"
            </div>
            <div style={{ marginTop: '8px' }}>or ask for help finding HCPs, editing interactions, or generating follow-ups.</div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: isLoading ? 'var(--color-warning)' : 'var(--color-success)',
              display: 'inline-block',
            }}
          />
          {isLoading
            ? 'AI agent processing...'
            : 'gpt-oss-20b via Groq · LangGraph agent ready'}
        </div>
        <div className="chat-input-row">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={2}
            placeholder="Describe interaction..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            id="chat-input"
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            id="chat-send-btn"
            title="Send message (Enter)"
          >
            {isLoading ? (
              <span
                style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid rgba(255,255,255,0.3)',
                  borderTop: '2px solid #fff',
                  borderRadius: '50%',
                  animation: 'spin 0.7s linear infinite',
                }}
              />
            ) : (
              '↑'
            )}
          </button>
        </div>
        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '5px' }}>
          Press Enter to send · Shift+Enter for new line · Chat data updates the left panel in real time
        </div>
      </div>
    </div>
  );
}
