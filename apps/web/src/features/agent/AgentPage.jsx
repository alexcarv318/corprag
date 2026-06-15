import { ChainlitContext } from "@chainlit/react-client";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppPreferences } from "../../hooks/useAppPreferences.js";
import TopActions from "../shell/TopActions.jsx";
import { getAgentConfig, makeChainlitApi } from "./client.js";
import { useAgentSession } from "./useAgentSession.js";

export default function AgentPage({ user, onSignOut }) {
  const { theme, setTheme } = useAppPreferences();
  const [menuOpen, setMenuOpen] = useState(false);
  const [configState, setConfigState] = useState({ status: "loading", config: null, error: "" });

  useEffect(() => {
    let alive = true;
    getAgentConfig()
      .then((config) => {
        if (alive) setConfigState({ status: "ready", config, error: "" });
      })
      .catch((error) => {
        if (alive) {
          setConfigState({
            status: "error",
            config: null,
            error: error.message || "Unable to load agent configuration."
          });
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  const api = useMemo(
    () => (configState.config ? makeChainlitApi(configState.config) : null),
    [configState.config]
  );

  if (configState.status === "loading") {
    return <div className="agent-loading">Loading agent</div>;
  }

  if (configState.status === "error") {
    return <div className="agent-loading error">{configState.error}</div>;
  }

  return (
    <ChainlitContext.Provider value={api}>
      <AgentWorkspace
        config={configState.config}
        user={user}
        onSignOut={onSignOut}
        theme={theme}
        setTheme={setTheme}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
      />
    </ChainlitContext.Provider>
  );
}

function AgentWorkspace({ config, user, onSignOut, theme, setTheme, menuOpen, setMenuOpen }) {
  const api = useMemo(() => makeChainlitApi(config), [config]);
  const agent = useAgentSession({ api, config });
  const [draft, setDraft] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const threadRef = useRef(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [agent.messages.length, agent.running]);

  function submitMessage(event) {
    event.preventDefault();
    if (!draft.trim() || agent.running) return;
    agent.sendMessage(draft);
    setDraft("");
  }

  return (
    <>
      <AgentSessionsDrawer agent={agent} />
      <main className="agent-page-main">
        <TopActions
          menuOpen={menuOpen}
          setMenuOpen={setMenuOpen}
          theme={theme}
          onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
          user={user}
          onSignOut={onSignOut}
          primaryLink={{ href: "/workflows", label: "Workflows", title: "Open workflows" }}
          showWorkflowSettings={false}
        />
        <section className="agent-thread" ref={threadRef} aria-live="polite">
          {agent.error ? <div className="agent-error">{agent.error}</div> : null}
          {!agent.messages.length ? (
            <AgentWelcome agent={agent} />
          ) : (
            <>
              <ConversationMessages messages={agent.messages} running={agent.running} />
              <AgentTaskLists tasklists={agent.tasklists} />
            </>
          )}
        </section>
        <form className="agent-composer" onSubmit={submitMessage}>
          <textarea
            value={draft}
            rows={2}
            placeholder="Type your message here..."
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) submitMessage(event);
            }}
          />
          <div className="agent-composer-bar">
            <div className="agent-config-wrap">
              <button
                className="agent-icon-button"
                type="button"
                title="Agent settings"
                aria-label="Agent settings"
                aria-expanded={settingsOpen}
                onClick={() => setSettingsOpen(!settingsOpen)}
              >
                <SettingsIcon />
              </button>
              <AgentSettingsPopover agent={agent} open={settingsOpen} />
            </div>
            <ModePills agent={agent} />
            <div className="agent-composer-spacer" />
            {agent.running ? (
              <button className="agent-stop-button" type="button" onClick={agent.stop} title="Stop" aria-label="Stop">
                <StopIcon />
              </button>
            ) : (
              <button className="agent-send-button" type="submit" disabled={!draft.trim() || !agent.connected}>
                <ArrowUpIcon />
              </button>
            )}
          </div>
        </form>
        <div className="agent-disclaimer">Corprag can make mistakes. Check important info.</div>
      </main>
    </>
  );
}

function AgentSessionsDrawer({ agent }) {
  const grouped = groupSessions(agent.sessions);

  return (
    <aside className="agent-sessions-drawer">
      <div className="sidebar-head">
        <div className="sidebar-head-row">
          <h1 className="sidebar-title">Agent</h1>
          <button className="sidebar-toggle" type="button" title="New chat" aria-label="New chat" onClick={agent.newChat}>
            <EditIcon />
          </button>
        </div>
        <div className="sidebar-meta">
          <span className={`status ${agent.connected ? "ok" : ""}`}>{agent.status}</span>
        </div>
        <label className="agent-session-search">
          <SearchIcon />
          <input
            type="search"
            value={agent.search}
            placeholder="Search chats"
            onChange={(event) => agent.setSearch(event.target.value)}
          />
        </label>
        <button className="agent-new-chat-button" type="button" onClick={agent.newChat}>
          New chat
        </button>
      </div>
      <div id="sidebar" className="sidebar-body agent-session-groups">
        {!agent.sessions.length ? <div className="agent-session-empty">No chats yet</div> : null}
        {Object.entries(grouped).map(([label, sessions]) => (
          <div className="group agent-session-group" key={label}>
            <div className="agent-session-group-label">{label}</div>
            {sessions.map((session) => (
              <div
                className={`item agent-session-row${session.id === agent.activeSessionId ? " active" : ""}`}
                key={session.id}
                title={session.title}
                onClick={() => agent.selectSession(session.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") agent.selectSession(session.id);
                }}
              >
                <span className="workflow-icon"><ChatIcon /></span>
                <span className="title">{session.title}</span>
                <button
                  className="agent-session-delete"
                  type="button"
                  title="Delete session"
                  aria-label="Delete session"
                  onClick={(event) => {
                    event.stopPropagation();
                    agent.deleteSession(session.id);
                  }}
                >
                  x
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}

function AgentWelcome({ agent }) {
  return (
    <div className="agent-welcome">
      <h1>{agent.activeMode?.label || "Agent"}</h1>
      <div className="agent-starter-grid">
        {agent.activeStarters.map((starter) => (
          <button key={starter.label} type="button" onClick={() => agent.sendMessage(starter.message)} disabled={agent.running}>
            <strong>{starter.label}</strong>
            <span>{starter.message}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ModePills({ agent }) {
  return (
    <div className="agent-mode-pills" aria-label="Agent mode">
      {agent.config.modes.map((mode) => (
        <button
          className={mode.id === agent.mode ? "active" : ""}
          key={mode.id}
          type="button"
          onClick={() => agent.setMode(mode.id)}
        >
          {mode.id === "internal" ? "Internal" : "Law"}
        </button>
      ))}
    </div>
  );
}

function AgentSettingsPopover({ agent, open }) {
  if (!open) return null;
  return (
    <div className="agent-settings-popover">
      <label>
        <span>Mode</span>
        <select value={agent.mode} onChange={(event) => agent.setMode(event.target.value)}>
          {agent.config.modes.map((mode) => (
            <option key={mode.id} value={mode.id}>{mode.label}</option>
          ))}
        </select>
      </label>
      <label>
        <span>Model</span>
        <select value={agent.modelId} onChange={(event) => agent.setModelId(event.target.value)}>
          {agent.config.models.map((model) => (
            <option key={model.id} value={model.id}>{model.label}</option>
          ))}
        </select>
      </label>
      {agent.activeMode?.supports_agent_versions ? (
        <label>
          <span>Agent version</span>
          <select value={agent.agentVersion} onChange={(event) => agent.setAgentVersion(event.target.value)}>
            {agent.config.agent_versions.map((version) => (
              <option key={version.id} value={version.id}>{version.label}</option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="agent-status-line">
        <span className={`agent-status-dot ${agent.connected ? "ok" : ""}`} />
        {agent.status}
      </div>
    </div>
  );
}

function ConversationMessages({ messages, running }) {
  const turns = groupMessagesByTurn(messages);
  return turns.map((turn, index) => (
    <div className="agent-turn" key={turn.id}>
      {turn.user ? <AgentMessage message={turn.user} /> : null}
      {turn.tools.length ? <ToolActivityGroup tools={turn.tools} active={running && index === turns.length - 1} /> : null}
      {turn.assistants.map((message) => <AgentMessage key={message.id} message={message} />)}
      {turn.orphans.map((message) => <AgentMessage key={message.id} message={message} />)}
    </div>
  ));
}

function ToolActivityGroup({ tools, active }) {
  const running = active || tools.some((tool) => tool.streaming);

  return (
    <details className={`agent-tool-activity${running ? " running" : ""}`}>
      <summary>
        <span className="agent-message-avatar" aria-hidden="true">A</span>
        <span className="agent-tool-activity-label">{running ? "Using tools" : "Used tools"}</span>
      </summary>
      <div className="agent-tool-activity-body">
        {tools.map((message) => <AgentMessage key={message.id} message={message} />)}
      </div>
    </details>
  );
}

function groupMessagesByTurn(messages) {
  const turns = [];
  let current = null;

  const ensureTurn = (message) => {
    if (!current) {
      current = {
        id: `turn-${message.id}`,
        user: null,
        tools: [],
        assistants: [],
        orphans: []
      };
      turns.push(current);
    }
    return current;
  };

  for (const message of messages) {
    if (message.role === "user") {
      current = {
        id: `turn-${message.id}`,
        user: message,
        tools: [],
        assistants: [],
        orphans: []
      };
      turns.push(current);
      continue;
    }

    const turn = ensureTurn(message);
    if (message.role === "tool") {
      turn.tools.push(message);
    } else if (message.role === "assistant") {
      turn.assistants.push(message);
    } else {
      turn.orphans.push(message);
    }
  }

  return turns;
}

function AgentMessage({ message }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const author = isUser ? "" : message.author || "Corprag";

  return (
    <article className={`agent-message ${message.role}`}>
      {!isUser ? (
        <div className="agent-message-avatar" aria-hidden="true">
          {isTool ? "T" : "A"}
        </div>
      ) : null}
      <div className="agent-message-body">
        {author ? <div className="agent-message-author">{author}</div> : null}
        <div className="agent-message-content">
          {isTool ? <ToolMessage message={message} /> : renderMarkdown(message.content)}
          {message.streaming ? <span className="agent-caret" /> : null}
        </div>
      </div>
    </article>
  );
}

function ToolMessage({ message }) {
  const [headline, ...details] = message.content.split("\n").filter(Boolean);
  return (
    <details className="agent-tool-card" open={message.streaming}>
      <summary>{headline || message.author || "Tool activity"}</summary>
      {details.length && <pre>{details.join("\n")}</pre>}
    </details>
  );
}

function AgentTaskLists({ tasklists }) {
  if (!tasklists?.length) return null;
  return (
    <div className="agent-tasklists">
      {tasklists.map((tasklist) => (
        <div className="agent-tasklist" key={tasklist.id}>
          <strong>{tasklist.name || tasklist.status || "Tasks"}</strong>
          {(tasklist.tasks || []).map((task) => (
            <span key={task.id || task.title}>{task.title}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

function renderMarkdown(content) {
  const lines = (content || "").split("\n");
  const blocks = [];
  let index = 0;
  while (index < lines.length) {
    if (isTableStart(lines, index)) {
      const table = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        table.push(lines[index]);
        index += 1;
      }
      blocks.push(renderTable(table));
      continue;
    }
    if (/^\s*\d+\.\s+/.test(lines[index])) {
      const items = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(<ol key={`ol-${index}`}>{items.map((item) => <li key={item}>{renderInline(item)}</li>)}</ol>);
      continue;
    }
    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !isTableStart(lines, index) && !/^\s*\d+\.\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    if (paragraph.length) {
      blocks.push(<p key={`p-${index}`}>{renderInline(paragraph.join(" "))}</p>);
    }
    index += 1;
  }
  return blocks;
}

function isTableStart(lines, index) {
  return lines[index]?.trim().startsWith("|") && lines[index + 1]?.includes("---");
}

function renderTable(lines) {
  const rows = lines
    .filter((line) => !/^\s*\|?\s*-+/.test(line))
    .map((line) => line.split("|").map((cell) => cell.trim()).filter(Boolean));
  const [head = [], ...body] = rows;
  return (
    <div className="agent-table-wrap" key={`table-${lines.join("").length}-${head.join("-")}`}>
      <table>
        <thead><tr>{head.map((cell) => <th key={cell}>{renderInline(cell)}</th>)}</tr></thead>
        <tbody>
          {body.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.join("-")}`}>
              {row.map((cell) => <td key={cell}>{renderInline(cell)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInline(text) {
  const parts = [];
  const pattern = /\[([^\]]+)]\(([^)]+)\)/g;
  let lastIndex = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(<a key={`${match[1]}-${match.index}`} href={match[2]}>{match[1]}</a>);
    lastIndex = pattern.lastIndex;
    match = pattern.exec(text);
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

function groupSessions(sessions) {
  const groups = {};
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (const session of sessions) {
    const date = new Date(session.updatedAt || session.createdAt);
    date.setHours(0, 0, 0, 0);
    const diff = Math.floor((today - date) / 86400000);
    const label = diff === 0 ? "Today" : diff <= 7 ? "Previous 7 days" : diff <= 30 ? "Previous 30 days" : "Older";
    (groups[label] = groups[label] || []).push(session);
  }
  return groups;
}

function SearchIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" /><path d="m20 20-3.7-3.7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>;
}

function EditIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 20h9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>;
}

function SettingsIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.8" /><path d="M19.4 15a1.8 1.8 0 0 0 .4 2l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.8 1.8 0 0 0-2-.4 1.8 1.8 0 0 0-1 1.6V21a2 2 0 1 1-4 0v-.1a1.8 1.8 0 0 0-1-1.6 1.8 1.8 0 0 0-2 .4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.8 1.8 0 0 0 .4-2 1.8 1.8 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.1a1.8 1.8 0 0 0 1.6-1 1.8 1.8 0 0 0-.4-2l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.8 1.8 0 0 0 2 .4 1.8 1.8 0 0 0 1-1.6V3a2 2 0 1 1 4 0v.1a1.8 1.8 0 0 0 1 1.6 1.8 1.8 0 0 0 2-.4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.8 1.8 0 0 0-.4 2 1.8 1.8 0 0 0 1.6 1h.1a2 2 0 1 1 0 4h-.1a1.8 1.8 0 0 0-1.6 1Z" stroke="currentColor" strokeWidth="1.45" /></svg>;
}

function ArrowUpIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 19V5" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" /><path d="m5 12 7-7 7 7" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function StopIcon() {
  return <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="1.5" /></svg>;
}

function ChatIcon() {
  return <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M21 12a8 8 0 0 1-8 8H7l-4 2 1.5-4A8 8 0 1 1 21 12Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>;
}
