import { useState } from "react";

import { getDocumentSource } from "../api/documents.js";
import { getEvidence } from "../api/workflows.js";
import { displayOptionValue } from "../features/workflows/shared/displayUtils.js";

export function useSourceDrawer() {
  const [drawer, setDrawer] = useState(null);

  async function openDocument(source) {
    const highlightChunkIds = source.chunk_ids || (source.chunk_id ? [source.chunk_id] : []);
    setDrawer((current) => ({
      title: current?.title || "Source",
      subtitle: current?.subtitle || source.file || "",
      ...current,
      sources: current?.sources?.length ? current.sources : [normalizeSource(source)],
      loading: true,
      error: ""
    }));
    try {
      const payload = await getDocumentSource(source.file);
      setDrawer((current) => ({
        ...current,
        loading: false,
        document: payload,
        highlightChunkIds,
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
      enrichSources(sources, payload.context || "");
    } catch (error) {
      setDrawer({ title: "Evidence", subtitle: payload.context || "", loading: false, error: error.message });
    }
  }

  function openSources(sources, context) {
    const normalizedSources = sources.map(normalizeSource);
    setDrawer({ title: "Sources", subtitle: context, sources: normalizedSources });
    enrichSources(normalizedSources, context);
  }

  async function enrichSources(sources, context) {
    const uniqueFiles = [...new Set(sources.map((source) => source.file).filter(Boolean))];
    const entries = await Promise.all(
      uniqueFiles.map(async (file) => {
        try {
          return [file, await getDocumentSource(file)];
        } catch {
          return [file, null];
        }
      })
    );
    const documentsByFile = Object.fromEntries(entries);
    setDrawer((current) => {
      if (!current?.sources) return current;
      return {
        ...current,
        subtitle: context,
        sources: current.sources.map((source) => {
          const document = documentsByFile[source.file];
          if (!document) return source;
          return {
            ...source,
            doc_type: source.doc_type || document.doc_type,
            title: source.title === source.file ? document.title || source.title : source.title,
            file: source.file
          };
        })
      };
    });
  }

  function closeDrawer() {
    setDrawer(null);
  }

  function backToSources() {
    setDrawer((current) => (current?.sources?.length ? { ...current, document: null, error: "" } : null));
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

function normalizeSource(source) {
  return {
    ...source,
    title: source.title || source.file,
    source_type: source.source_type || source.doc_type,
    source_label: source.source_label || displayOptionValue(source.doc_type || source.link_type || "")
  };
}
