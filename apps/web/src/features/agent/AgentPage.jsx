import { ChainlitContext } from "@chainlit/react-client";
import { useEffect, useMemo, useRef, useState } from "react";

import { useSourceDrawer } from "../../hooks/useSourceDrawer.js";
import { useAppPreferences } from "../../hooks/useAppPreferences.js";
import SidebarToggleIcon from "../shell/SidebarToggleIcon.jsx";
import TopActions from "../shell/TopActions.jsx";
import DocumentSourceDrawer from "../documents/DocumentSourceDrawer.jsx";
import { getAgentConfig, makeChainlitApi } from "./client.js";
import { useAgentSession } from "../../hooks/useAgentSession.js";

export default function AgentPage({ user, onSignOut }) {
  const { theme, setTheme, collapsed, setCollapsed } = useAppPreferences();
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
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
      />
    </ChainlitContext.Provider>
  );
}

function AgentWorkspace({ config, user, onSignOut, theme, setTheme, collapsed, setCollapsed, menuOpen, setMenuOpen }) {
  const api = useMemo(() => makeChainlitApi(config), [config]);
  const agent = useAgentSession({ api, config });
  const [draft, setDraft] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const threadRef = useRef(null);
  const textareaRef = useRef(null);
  const { drawer, openDocument, openSources, closeDrawer, backToSources } = useSourceDrawer();
  const [sourceLayoutState, setSourceLayoutState] = useState("closed");

  useEffect(() => {
    document.body.classList.remove("workflow-sidebar-collapsed");
    document.body.classList.toggle("agent-sidebar-collapsed", collapsed);
    return () => document.body.classList.remove("agent-sidebar-collapsed");
  }, [collapsed]);

  useEffect(() => {
    if (drawer) {
      setSourceLayoutState((current) => (current === "open" ? "open" : "opening"));
      const frame = window.requestAnimationFrame(() => setSourceLayoutState("open"));
      return () => window.cancelAnimationFrame(frame);
    }
    setSourceLayoutState((current) => (current === "open" || current === "opening" ? "closing" : "closed"));
    const timeout = window.setTimeout(() => setSourceLayoutState("closed"), 180);
    return () => window.clearTimeout(timeout);
  }, [drawer]);

  useEffect(() => {
    document.body.classList.toggle("agent-sources-open", sourceLayoutState === "open");
    document.body.classList.toggle("agent-sources-opening", sourceLayoutState === "opening");
    document.body.classList.toggle("agent-sources-closing", sourceLayoutState === "closing");
    return () => {
      document.body.classList.remove("agent-sources-open");
      document.body.classList.remove("agent-sources-opening");
      document.body.classList.remove("agent-sources-closing");
    };
  }, [sourceLayoutState]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [agent.messages.length, agent.running]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 170)}px`;
  }, [draft]);

  function submitMessage(event) {
    event.preventDefault();
    if (!draft.trim() || agent.running) return;
    agent.sendMessage(draft);
    setDraft("");
  }

  function openAgentSource(source, sources) {
    const sourceList = sources?.length ? sources : [source];
    openSources(sourceList, "Cited documents");
    openDocument(source);
  }

  return (
    <>
      <AgentSessionsDrawer
        agent={agent}
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
      />
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
          {agent.resuming ? (
            <AgentThreadLoading />
          ) : !agent.messages.length ? (
            <AgentWelcome agent={agent} />
          ) : (
            <>
              <ConversationMessages messages={agent.messages} running={agent.running} onSourceOpen={openAgentSource} />
              <AgentTaskLists tasklists={agent.tasklists} />
            </>
          )}
        </section>
        <form className="agent-composer" onSubmit={submitMessage}>
          <textarea
            ref={textareaRef}
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
      <DocumentSourceDrawer
        className="agent-sources-drawer"
        drawer={drawer}
        onBack={backToSources}
        onClose={closeDrawer}
        onOpenDocument={openDocument}
      />
    </>
  );
}

function AgentSessionsDrawer({ agent, collapsed, onToggle }) {
  const grouped = groupSessions(agent.sessions);

  return (
    <aside className={`agent-sessions-drawer${collapsed ? " collapsed" : ""}`}>
      <div className="sidebar-head">
        <div className="sidebar-head-row">
          <h1 className="sidebar-title">Agent</h1>
          <div className="agent-sidebar-actions">
            <button
              className="sidebar-toggle"
              type="button"
              title={collapsed ? "Show sessions" : "Hide sessions"}
              aria-label={collapsed ? "Show sessions" : "Hide sessions"}
              aria-expanded={!collapsed}
              onClick={onToggle}
            >
              <SidebarToggleIcon collapsed={collapsed} />
            </button>
            <button className="sidebar-toggle agent-new-chat-icon" type="button" title="New chat" aria-label="New chat" onClick={agent.newChat}>
              <NewChatIcon />
            </button>
          </div>
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

function AgentThreadLoading() {
  return <div className="agent-thread-loading">Loading chat</div>;
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

function ConversationMessages({ messages, running, onSourceOpen }) {
  const turns = groupMessagesByTurn(messages);
  return turns.map((turn, index) => (
    <div className="agent-turn" key={turn.id}>
      {turn.user ? <AgentMessage message={turn.user} onSourceOpen={onSourceOpen} /> : null}
      {turn.tools.length ? <ToolActivityGroup tools={turn.tools} active={running && index === turns.length - 1} onSourceOpen={onSourceOpen} /> : null}
      {turn.assistants.map((message) => <AgentMessage key={message.id} message={message} onSourceOpen={onSourceOpen} />)}
      {turn.orphans.map((message) => <AgentMessage key={message.id} message={message} onSourceOpen={onSourceOpen} />)}
    </div>
  ));
}

function ToolActivityGroup({ tools, active, onSourceOpen }) {
  const running = active || tools.some((tool) => tool.streaming);

  return (
    <details className={`agent-tool-activity${running ? " running" : ""}`}>
      <summary>
        <span className="agent-message-avatar" aria-hidden="true">A</span>
        <span className="agent-tool-activity-label">{running ? "Using tools" : "Used tools"}</span>
      </summary>
      <div className="agent-tool-activity-body">
        {tools.map((message) => <AgentMessage key={message.id} message={message} onSourceOpen={onSourceOpen} />)}
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

function AgentMessage({ message, onSourceOpen }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const author = isUser ? "" : message.author || "Corprag";
  const messageSources = useMemo(() => sourcesFromContent(message.content), [message.content]);

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
          {isTool ? <ToolMessage message={message} /> : renderMarkdown(message.content, onSourceOpen, messageSources)}
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

function renderMarkdown(content, onSourceOpen, messageSources = []) {
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
      blocks.push(renderTable(table, onSourceOpen, messageSources));
      continue;
    }
    const heading = lines[index].match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const Level = `h${heading[1].length + 1}`;
      blocks.push(<Level className="agent-markdown-heading" key={`h-${index}`}>{renderInline(heading[2], onSourceOpen, messageSources)}</Level>);
      index += 1;
      continue;
    }
    if (/^\s*[-*]\s+/.test(lines[index])) {
      const items = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*]\s+/, ""));
        index += 1;
      }
      blocks.push(<ul key={`ul-${index}`}>{items.map((item) => <li key={item}>{renderInline(item, onSourceOpen, messageSources)}</li>)}</ul>);
      continue;
    }
    if (/^\s*\d+\.\s+/.test(lines[index])) {
      const items = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+\.\s+/, ""));
        index += 1;
      }
      blocks.push(<ol key={`ol-${index}`}>{items.map((item) => <li key={item}>{renderInline(item, onSourceOpen, messageSources)}</li>)}</ol>);
      continue;
    }
    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !isTableStart(lines, index) && !/^(#{1,4})\s+/.test(lines[index]) && !/^\s*[-*]\s+/.test(lines[index]) && !/^\s*\d+\.\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    if (paragraph.length) {
      blocks.push(<p key={`p-${index}`}>{renderInline(paragraph.join(" "), onSourceOpen, messageSources)}</p>);
    }
    index += 1;
  }
  return blocks;
}

function isTableStart(lines, index) {
  return lines[index]?.trim().startsWith("|") && lines[index + 1]?.includes("---");
}

function renderTable(lines, onSourceOpen, messageSources) {
  const rows = lines
    .filter((line) => !/^\s*\|?\s*-+/.test(line))
    .map((line) => line.split("|").map((cell) => cell.trim()).filter(Boolean));
  const [head = [], ...body] = rows;
  return (
    <div className="agent-table-wrap" key={`table-${lines.join("").length}-${head.join("-")}`}>
      <table>
        <thead><tr>{head.map((cell) => <th key={cell}>{renderInline(cell, onSourceOpen, messageSources)}</th>)}</tr></thead>
        <tbody>
          {body.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.join("-")}`}>
              {row.map((cell) => <td key={cell}>{renderInline(cell, onSourceOpen, messageSources)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInline(text, onSourceOpen, messageSources = []) {
  const parts = [];
  const pattern = /(\[([^\]]+)]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let lastIndex = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    if (match[2]) {
      const source = sourceFromCitationHref(match[3]);
      parts.push(
        <a
          className={source ? "agent-citation-link" : undefined}
          href={match[3]}
          key={`a-${match.index}-${match[2]}`}
          title={source ? "Open source document" : undefined}
          onClick={source && onSourceOpen ? (event) => {
            event.preventDefault();
            onSourceOpen(source, messageSources);
          } : undefined}
        >
          {match[2]}
        </a>
      );
    } else if (match[4]) {
      parts.push(<strong key={`strong-${match.index}`}>{match[4]}</strong>);
    } else if (match[5]) {
      parts.push(<code key={`code-${match.index}`}>{match[5]}</code>);
    }
    lastIndex = pattern.lastIndex;
    match = pattern.exec(text);
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

function sourcesFromContent(content) {
  const sources = [];
  const seen = new Set();
  const pattern = /\[([^\]]+)]\(([^)]+)\)/g;
  let match = pattern.exec(content || "");
  while (match) {
    const source = sourceFromCitationHref(match[2]);
    if (source) {
      const key = `${source.file}:${source.chunk_id || ""}`;
      if (!seen.has(key)) {
        seen.add(key);
        sources.push(source);
      }
    }
    match = pattern.exec(content || "");
  }
  return sources;
}

function sourceFromCitationHref(href) {
  if (!href.includes("agent-source") && !href.includes("corprag-source")) return null;
  const queryStart = href.indexOf("?");
  if (queryStart < 0) return null;
  const queryString = href.slice(queryStart + 1).split("#")[0];
  const params = new URLSearchParams(queryString);
  const file = params.get("file");
  if (!file) return null;
  const chunk = params.get("chunk") || "";
  return {
    file,
    title: file,
    chunk_id: chunk || undefined
  };
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
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 7.5A3.5 3.5 0 0 1 8.5 4h7A3.5 3.5 0 0 1 19 7.5v5A3.5 3.5 0 0 1 15.5 16H11l-4 3v-3.2A3.5 3.5 0 0 1 5 12.5v-5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

function NewChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M5 7.5A3.5 3.5 0 0 1 8.5 4h7A3.5 3.5 0 0 1 19 7.5v5A3.5 3.5 0 0 1 15.5 16H11l-4 3v-3.2A3.5 3.5 0 0 1 5 12.5v-5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M12 7.6v4.8M9.6 10h4.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
