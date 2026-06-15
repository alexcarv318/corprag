import {
  messagesState,
  useChatData,
  useChatInteract,
  useChatMessages,
  useChatSession
} from "@chainlit/react-client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSetRecoilState } from "recoil";

import { createAgentHandoff, flattenSteps, makeId, normalizeStep, nowIso } from "../features/agent/client.js";

function settingsFor({ mode, modelId, agentVersion }) {
  const settings = {
    Mode: mode,
    Model: modelId
  };
  if (mode === "internal") settings.AgentVersion = agentVersion;
  return settings;
}

function threadTitle(thread) {
  if (thread.name) return thread.name;
  const firstUserStep = (thread.steps || []).find((step) => step.type === "user_message" && step.output);
  return firstUserStep?.output || "New chat";
}

function updatedAt(thread) {
  const steps = thread.steps || [];
  return steps[steps.length - 1]?.createdAt || thread.createdAt || nowIso();
}

function normalizeThread(thread) {
  return {
    id: thread.id,
    title: threadTitle(thread).trim().replace(/\s+/g, " ").slice(0, 84),
    createdAt: thread.createdAt,
    updatedAt: updatedAt(thread),
    raw: thread
  };
}

export function useAgentSession({ api, config }) {
  const { connect, disconnect, idToResume } = useChatSession();
  const {
    clear,
    sendMessage: sendChainlitMessage,
    setIdToResume,
    stopTask,
    updateChatSettings
  } = useChatInteract();
  const { connected, error, loading, tasklists, actions } = useChatData();
  const { messages: chainlitMessages, threadId } = useChatMessages();
  const setChainlitMessages = useSetRecoilState(messagesState);
  const [mode, setMode] = useState(config.default_mode);
  const [modelId, setModelId] = useState(config.default_model_id);
  const [agentVersion, setAgentVersion] = useState(config.default_agent_version);
  const [threads, setThreads] = useState([]);
  const [search, setSearch] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [pendingResumeId, setPendingResumeId] = useState(null);
  const [freshChatNonce, setFreshChatNonce] = useState(0);
  const connectSessionRef = useRef(null);
  const disconnectRef = useRef(null);
  const fetchThreadsRef = useRef(null);
  const freshChatNonceRef = useRef(0);

  const messages = useMemo(
    () => flattenSteps(chainlitMessages).map(normalizeStep).filter(Boolean),
    [chainlitMessages]
  );
  const activeMode = useMemo(() => config.modes.find((candidate) => candidate.id === mode), [config.modes, mode]);
  const activeStarters = useMemo(() => config.starters?.[mode] || [], [config.starters, mode]);

  const fetchThreads = useCallback(async (query) => {
    const response = await api.listThreads(
      { first: 60 },
      { search: query.trim() || undefined }
    );
    setThreads((response.data || []).map(normalizeThread));
  }, [api]);

  const refreshThreads = useCallback(async () => {
    await fetchThreads(search);
  }, [fetchThreads, search]);

  const connectSession = useCallback(async () => {
    await createAgentHandoff();
    await api.headerAuth();
    await connect({ transports: ["websocket", "polling"], userEnv: {} });
  }, [api, connect]);

  useEffect(() => {
    connectSessionRef.current = connectSession;
    disconnectRef.current = disconnect;
    fetchThreadsRef.current = fetchThreads;
  }, [connectSession, disconnect, fetchThreads]);

  useEffect(() => {
    let alive = true;
    connectSessionRef.current()
      .then(() => fetchThreadsRef.current(""))
      .catch((requestError) => {
        if (alive) setConnectionError(requestError.message || "Agent connection failed.");
      });
    return () => {
      alive = false;
      disconnectRef.current();
    };
  }, []);

  useEffect(() => {
    if (!freshChatNonce || freshChatNonce === freshChatNonceRef.current) return;
    freshChatNonceRef.current = freshChatNonce;
    connectSessionRef.current().catch((requestError) => {
      setConnectionError(requestError.message || "Agent connection failed.");
    });
  }, [freshChatNonce]);

  useEffect(() => {
    if (!connected) return;
    updateChatSettings(settingsFor({ mode, modelId, agentVersion }));
  }, [agentVersion, connected, mode, modelId, updateChatSettings]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      refreshThreads().catch((requestError) => {
        setConnectionError(requestError.message || "Unable to load sessions.");
      });
    }, 180);
    return () => window.clearTimeout(timeout);
  }, [refreshThreads]);

  useEffect(() => {
    if (!pendingResumeId || idToResume !== pendingResumeId) return;
    disconnectRef.current();
    connectSessionRef.current()
      .catch((requestError) => {
        setConnectionError(requestError.message || "Unable to resume session.");
        setPendingResumeId(null);
      });
  }, [idToResume, pendingResumeId]);

  useEffect(() => {
    if (!pendingResumeId || threadId !== pendingResumeId || !messages.length) return;
    setPendingResumeId(null);
  }, [messages.length, pendingResumeId, threadId]);

  useEffect(() => {
    if (!pendingResumeId || threadId !== pendingResumeId) return undefined;
    const timeout = window.setTimeout(() => setPendingResumeId(null), 1800);
    return () => window.clearTimeout(timeout);
  }, [pendingResumeId, threadId]);

  useEffect(() => {
    if (!threadId || loading) return;
    refreshThreads().catch(() => {});
  }, [loading, refreshThreads, threadId]);

  const sendMessage = useCallback(
    (content) => {
      const trimmed = content.trim();
      if (!trimmed || loading) return;
      sendChainlitMessage({
        id: makeId(),
        threadId: threadId || "",
        parentId: null,
        name: "User",
        type: "user_message",
        output: trimmed,
        createdAt: nowIso(),
        metadata: {}
      });
    },
    [loading, sendChainlitMessage, threadId]
  );

  const newChat = useCallback(() => {
    setPendingResumeId(null);
    setIdToResume(undefined);
    clear();
    setChainlitMessages([]);
    setFreshChatNonce((nonce) => nonce + 1);
  }, [clear, setChainlitMessages, setIdToResume]);

  const selectSession = useCallback(
    (selectedThreadId) => {
      if (!selectedThreadId || selectedThreadId === threadId) return;
      clear();
      setChainlitMessages([]);
      setIdToResume(selectedThreadId);
      setPendingResumeId(selectedThreadId);
    },
    [clear, setChainlitMessages, setIdToResume, threadId]
  );

  const deleteSession = useCallback(
    async (selectedThreadId) => {
      await api.deleteThread(selectedThreadId);
      if (selectedThreadId === threadId) {
        newChat();
      }
      await refreshThreads();
    },
    [api, newChat, refreshThreads, threadId]
  );

  return {
    actions,
    activeMode,
    activeSessionId: pendingResumeId || threadId,
    activeStarters,
    agentVersion,
    config,
    connected,
    error: connectionError || (error ? "Agent connection failed." : ""),
    messages,
    mode,
    modelId,
    resuming: Boolean(pendingResumeId),
    running: loading,
    search,
    sessions: threads,
    setAgentVersion,
    setMode,
    setModelId,
    setSearch,
    status: connected ? "connected" : "connecting",
    tasklists,
    deleteSession,
    newChat,
    refreshThreads,
    selectSession,
    sendMessage,
    stop: stopTask
  };
}
