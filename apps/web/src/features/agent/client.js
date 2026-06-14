import { io } from "socket.io-client";

import { apiFetch } from "../../api/client.js";

function makeId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function nowIso() {
  return new Date().toISOString();
}

const VISIBLE_ASSISTANT_AUTHORS = new Set(["Assistant", "Corprag", "Lawrag"]);

function stepOutput(step) {
  return typeof step.output === "string" ? step.output : "";
}

export function getAgentConfig() {
  return apiFetch("/api/agent/config");
}

export function createAgentHandoff() {
  return apiFetch("/api/agent/handoff", { method: "POST" });
}

export class ChainlitAgentClient {
  constructor({ onEvent, onError }) {
    this.onEvent = onEvent;
    this.onError = onError;
    this.socket = null;
    this.sessionId = makeId();
  }

  async connect({ config, mode, modelId, agentVersion }) {
    await createAgentHandoff();
    const authResponse = await fetch(`${config.runtime_path}/auth/header`, {
      method: "POST",
      credentials: "same-origin"
    });
    if (!authResponse.ok) {
      throw new Error(`Agent runtime authentication failed (${authResponse.status})`);
    }

    const auth = {
      sessionId: this.sessionId,
      userEnv: JSON.stringify({}),
      clientType: "webapp",
      chatProfile: null,
      threadId: null
    };

    this.socket = io({
      path: `${config.runtime_path}/ws/socket.io`,
      transports: ["websocket", "polling"],
      withCredentials: true,
      auth
    });

    this.socket.on("connect", () => {
      this.onEvent({ type: "connected" });
      this.socket.emit("connection_successful");
      this.updateSettings({ mode, modelId, agentVersion });
    });
    this.socket.on("connect_error", (error) => this.handleError(error));
    this.socket.on("disconnect", () => this.onEvent({ type: "disconnected" }));
    this.socket.on("task_start", () => this.onEvent({ type: "run_started" }));
    this.socket.on("task_end", () => this.onEvent({ type: "run_finished" }));
    this.socket.on("new_message", (message) => this.onEvent({ type: "message", message }));
    this.socket.on("update_message", (message) => this.onEvent({ type: "message", message }));
    this.socket.on("stream_start", (message) => this.onEvent({ type: "message", message }));
    this.socket.on("stream_token", (token) => this.onEvent({ type: "token", token }));
    this.socket.on("actions", (actions) => this.onEvent({ type: "actions", actions }));
    this.socket.on("chat_settings", (settings) => this.onEvent({ type: "settings", settings }));
  }

  disconnect() {
    if (!this.socket) return;
    this.socket.disconnect();
    this.socket = null;
  }

  clear() {
    this.socket?.emit("clear_session");
    this.sessionId = makeId();
  }

  stop() {
    this.socket?.emit("stop");
  }

  send(content) {
    const message = {
      id: makeId(),
      threadId: "",
      parentId: null,
      name: "User",
      type: "user_message",
      output: content,
      createdAt: nowIso(),
      metadata: {}
    };
    this.onEvent({ type: "message", message });
    this.socket?.emit("client_message", { message, fileReferences: null });
  }

  updateSettings({ mode, modelId, agentVersion }) {
    const settings = {
      Mode: mode,
      Model: modelId
    };
    if (mode === "internal") {
      settings.AgentVersion = agentVersion;
    }
    this.socket?.emit("chat_settings_change", settings);
  }

  handleError(error) {
    this.onError?.(error);
    this.onEvent({ type: "error", error: error.message || "Agent connection failed" });
  }
}

export function normalizeStep(step) {
  const content = stepOutput(step);
  if (!isVisibleStep(step, content)) return null;

  return {
    id: step.id,
    role: stepRole(step),
    author: step.name,
    content,
    createdAt: step.createdAt || nowIso(),
    streaming: Boolean(step.streaming),
    raw: step
  };
}

function isVisibleStep(step, content) {
  if (!step?.id) return false;
  if (step.type === "user_message") return Boolean(content.trim());
  if (step.type !== "assistant_message") return false;
  if (isToolAuthor(step.name)) return Boolean(content.trim());
  if (!VISIBLE_ASSISTANT_AUTHORS.has(step.name)) return false;
  return Boolean(content.trim()) || Boolean(step.streaming);
}

function stepRole(step) {
  if (step.type === "user_message") return "user";
  if (isToolAuthor(step.name)) return "tool";
  return "assistant";
}

function isToolAuthor(author) {
  return typeof author === "string" && author.startsWith("Tool · ");
}
