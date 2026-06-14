import { useState } from "react";

import { getDocumentSource } from "../api/documents.js";
import { getEvidence } from "../api/workflows.js";

export function useSourceDrawer() {
  const [drawer, setDrawer] = useState(null);

  async function openDocument(source) {
    setDrawer((current) => ({ ...current, loading: true, error: "" }));
    try {
      const payload = await getDocumentSource(source.file);
      setDrawer((current) => ({
        ...current,
        loading: false,
        document: payload,
        highlightChunkIds: source.chunk_id ? [source.chunk_id] : [],
        highlightTerms: current?.highlightTerms || []
      }));
    } catch (error) {
      setDrawer((current) => ({ ...current, loading: false, error: error.message }));
    }
  }

  async function openEvidence(payload) {
    setDrawer({ title: "Evidence", subtitle: payload.context || "", loading: true, sources: [] });
    try {
      const evidence = await getEvidence(payload);
      const sources = (evidence.chunks || []).map((chunk) => ({
        file: chunk.file || payload.files?.[0],
        chunk_id: chunk.chunk_id,
        title: chunk.title
      })).filter((source) => source.file);
      setDrawer({
        title: "Evidence",
        subtitle: payload.context || "",
        sources,
        loading: false,
        highlightTerms: evidence.highlight_terms || [],
        highlightChunkIds: sources.map((source) => source.chunk_id).filter(Boolean)
      });
    } catch (error) {
      setDrawer({ title: "Evidence", subtitle: payload.context || "", loading: false, error: error.message });
    }
  }

  function openSources(sources, context) {
    setDrawer({ title: "Sources", subtitle: context, sources });
  }

  function closeDrawer() {
    setDrawer(null);
  }

  function backToSources() {
    setDrawer((current) => (current ? { ...current, document: null, error: "" } : null));
  }

  return {
    drawer,
    openDocument,
    openEvidence,
    openSources,
    closeDrawer,
    backToSources
  };
}
