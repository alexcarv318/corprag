import { ChainlitAPI } from "@chainlit/react-client";

import { apiFetch } from "../../api/client.js";

export function makeId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export const VISIBLE_ASSISTANT_AUTHORS = new Set(["Assistant", "Corprag", "Lawrag"]);

function stepOutput(step) {
  return typeof step.output === "string" ? step.output : "";
}

export function getAgentConfig() {
  return apiFetch("/api/agent/config");
}

export function createAgentHandoff() {
  return apiFetch("/api/agent/handoff", { method: "POST" });
}

export function makeChainlitApi(config) {
  const endpoint = `${window.location.origin}${config.runtime_path}`;
  return new ChainlitAPI(endpoint, "webapp");
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

export function flattenSteps(steps) {
  const flattened = [];
  const visit = (step) => {
    if (!step) return;
    flattened.push(step);
    if (Array.isArray(step.steps)) {
      step.steps.forEach(visit);
    }
  };
  steps.forEach(visit);
  return flattened;
}

function isVisibleStep(step, content) {
  if (!step?.id) return false;
  if (step.type === "user_message") return Boolean(content.trim());
  if (step.type === "tool") return Boolean(content.trim()) || Boolean(step.input);
  if (isToolAuthor(step.name)) return Boolean(content.trim()) || Boolean(step.input);
  if (step.type !== "assistant_message") return false;
  if (!VISIBLE_ASSISTANT_AUTHORS.has(step.name)) return false;
  return Boolean(content.trim()) || Boolean(step.streaming);
}

function stepRole(step) {
  if (step.type === "user_message") return "user";
  if (step.type === "tool") return "tool";
  if (isToolAuthor(step.name)) return "tool";
  return "assistant";
}

function isToolAuthor(author) {
  return typeof author === "string" && author.startsWith("Tool · ");
}
