import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChainlitAgentClient, getAgentConfig, normalizeStep } from "./client.js";

function upsertMessage(messages, next) {
  const index = messages.findIndex((message) => message.id === next.id);
  if (index === -1) return [...messages, next];
  return messages.map((message, currentIndex) => (currentIndex === index ? { ...message, ...next } : message));
}

function appendToken(messages, token) {
  if (!token?.id) return messages;
  if (!messages.some((message) => message.id === token.id)) {
    return [
      ...messages,
      {
        id: token.id,
        role: "assistant",
        author: "Assistant",
        content: token.token || "",
        createdAt: new Date().toISOString(),
        streaming: true,
        raw: token
      }
    ];
  }
  return messages.map((message) => {
    if (message.id !== token.id) return message;
    const content = token.isSequence ? token.token : `${message.content || ""}${token.token}`;
    return { ...message, content, streaming: true };
  });
}

export function useAgentSession() {
  const clientRef = useRef(null);
  const [config, setConfig] = useState(null);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState("internal");
  const [modelId, setModelId] = useState("");
  const [agentVersion, setAgentVersion] = useState("");

  useEffect(() => {
    let alive = true;
    getAgentConfig()
      .then((payload) => {
        if (!alive) return;
        setConfig(payload);
        setMode(payload.default_mode);
        setModelId(payload.default_model_id);
        setAgentVersion(payload.default_agent_version);
        setStatus("ready");
      })
      .catch((requestError) => {
        if (!alive) return;
        setError(requestError.message || "Unable to load agent configuration.");
        setStatus("error");
      });
    return () => {
      alive = false;
    };
  }, []);

  const handleEvent = useCallback((event) => {
    if (event.type === "connected") {
      setStatus("connected");
      setError("");
      return;
    }
    if (event.type === "disconnected") {
      setStatus("disconnected");
      return;
    }
    if (event.type === "run_started") {
      setRunning(true);
      return;
    }
    if (event.type === "run_finished") {
      setRunning(false);
      setMessages((current) => current.map((message) => ({ ...message, streaming: false })));
      return;
    }
    if (event.type === "message") {
      const normalized = normalizeStep(event.message);
      if (!normalized) return;
      setMessages((current) => upsertMessage(current, normalized));
      return;
    }
    if (event.type === "token") {
      setMessages((current) => appendToken(current, event.token));
      return;
    }
    if (event.type === "error") {
      setError(event.error);
      setRunning(false);
    }
  }, []);

  const connect = useCallback(async () => {
    if (!config) return;
    clientRef.current?.disconnect();
    const client = new ChainlitAgentClient({
      onEvent: handleEvent,
      onError: (connectionError) => setError(connectionError.message || "Agent connection failed.")
    });
    clientRef.current = client;
    setStatus("connecting");
    await client.connect({ config, mode, modelId, agentVersion });
  }, [agentVersion, config, handleEvent, mode, modelId]);

  useEffect(() => {
    if (!config || !modelId || !agentVersion) return undefined;
    connect().catch((connectionError) => {
      setError(connectionError.message || "Agent connection failed.");
      setStatus("error");
    });
    return () => {
      clientRef.current?.disconnect();
    };
  }, [agentVersion, config, connect, modelId]);

  useEffect(() => {
    clientRef.current?.updateSettings({ mode, modelId, agentVersion });
  }, [agentVersion, mode, modelId]);

  const sendMessage = useCallback((content) => {
    if (!content.trim()) return;
    clientRef.current?.send(content.trim());
  }, []);

  const stop = useCallback(() => {
    clientRef.current?.stop();
  }, []);

  const newChat = useCallback(() => {
    clientRef.current?.clear();
    setMessages([]);
  }, []);

  const activeStarters = useMemo(() => config?.starters?.[mode] || [], [config, mode]);
  const activeMode = useMemo(
    () => config?.modes?.find((candidate) => candidate.id === mode),
    [config, mode]
  );

  return {
    activeMode,
    activeStarters,
    agentVersion,
    config,
    error,
    messages,
    mode,
    modelId,
    running,
    setAgentVersion,
    setMode,
    setModelId,
    status,
    sendMessage,
    stop,
    newChat
  };
}
