import { useState } from "react";

import { useAgentSession } from "./useAgentSession.js";

export default function AgentPage({ user, onSignOut, onOpenWorkflows }) {
  const agent = useAgentSession();
  const [draft, setDraft] = useState("");

  function submitMessage(event) {
    event.preventDefault();
    if (!draft.trim() || agent.running) return;
    agent.sendMessage(draft);
    setDraft("");
  }

  return (
    <div className="agent-shell">
      <aside className="agent-sidebar">
        <div className="agent-sidebar-head">
          <h1>Agent</h1>
          <span className={`agent-status ${agent.status}`}>{agent.status}</span>
        </div>
        <button className="agent-new-chat" type="button" onClick={agent.newChat}>
          New chat
        </button>
        <div className="agent-control-group">
          <label>
            <span>Mode</span>
            <select value={agent.mode} onChange={(event) => agent.setMode(event.target.value)}>
              {(agent.config?.modes || []).map((mode) => (
                <option key={mode.id} value={mode.id}>{mode.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <select value={agent.modelId} onChange={(event) => agent.setModelId(event.target.value)}>
              {(agent.config?.models || []).map((model) => (
                <option key={model.id} value={model.id}>{model.label}</option>
              ))}
            </select>
          </label>
          {agent.activeMode?.supports_agent_versions ? (
            <label>
              <span>Agent version</span>
              <select value={agent.agentVersion} onChange={(event) => agent.setAgentVersion(event.target.value)}>
                {(agent.config?.agent_versions || []).map((version) => (
                  <option key={version.id} value={version.id}>{version.label}</option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <div className="agent-starters">
          {agent.activeStarters.map((starter) => (
            <button key={starter.label} type="button" onClick={() => agent.sendMessage(starter.message)} disabled={agent.running}>
              <strong>{starter.label}</strong>
              <span>{starter.message}</span>
            </button>
          ))}
        </div>
      </aside>

      <main className="agent-main">
        <header className="agent-topbar">
          <button type="button" className="agent-nav-button" onClick={onOpenWorkflows}>
            Workflows
          </button>
          <div className="agent-account">
            <span>{user?.username}</span>
            <button type="button" onClick={onSignOut}>Sign out</button>
          </div>
        </header>

        <section className="agent-thread" aria-live="polite">
          {agent.error ? <div className="agent-error">{agent.error}</div> : null}
          {!agent.messages.length ? (
            <div className="agent-empty">
              <h2>{agent.activeMode?.label || "Agent"}</h2>
              <p>Select a starter or ask a question.</p>
            </div>
          ) : (
            agent.messages.map((message) => <AgentMessage key={message.id} message={message} />)
          )}
        </section>

        <form className="agent-composer" onSubmit={submitMessage}>
          <textarea
            value={draft}
            rows={3}
            placeholder="Ask about the corporate archive or Swiss law..."
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                submitMessage(event);
              }
            }}
          />
          <div className="agent-composer-actions">
            {agent.running ? (
              <button type="button" className="agent-secondary-button" onClick={agent.stop}>
                Stop
              </button>
            ) : null}
            <button type="submit" disabled={!draft.trim() || agent.running || agent.status === "error"}>
              Send
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

function AgentMessage({ message }) {
  const roleLabel = message.role === "user" ? "You" : message.author || "Assistant";
  return (
    <article className={`agent-message ${message.role}`}>
      <div className="agent-message-author">{roleLabel}</div>
      <div className="agent-message-content">
        {renderMessageContent(message.content)}
        {message.streaming ? <span className="agent-caret" /> : null}
      </div>
    </article>
  );
}

function renderMessageContent(content) {
  if (!content) return null;
  return content.split("\n").map((line, index) => (
    <p key={`${index}-${line.slice(0, 12)}`}>{line || "\u00a0"}</p>
  ));
}
