import { useEffect, useState } from "react";

import { getDocumentSource } from "../../api/documents.js";
import { getCatalog, getDisclaimer, getEvidence, getWorkflow, runWorkflow } from "../../api/workflows.js";
import { DataModelGuide } from "../dataModel/DataModelGuide.jsx";
import DocumentSourceDrawer from "../documents/DocumentSourceDrawer.jsx";
import DisclaimerOverlay from "../shell/DisclaimerOverlay.jsx";
import Sidebar from "../shell/Sidebar.jsx";
import TopActions from "../shell/TopActions.jsx";
import WorkflowForm from "./WorkflowForm.jsx";
import WorkflowHeader from "./WorkflowHeader.jsx";
import WorkflowResults from "./WorkflowResults.jsx";
import { collectRunParameters, initialParameters } from "./workflowUtils.js";
import { summarizeResult } from "./resultUtils.js";
import { GLOBAL_CANCEL_KEY, loadTheme, saveTheme, SIDEBAR_COLLAPSED_KEY, setStorageBool, storageBool } from "../../utils/storage.js";
import { workflowFromUrl, syncWorkflowToUrl } from "../../utils/queryString.js";

export default function WorkflowConsole() {
  const [theme, setTheme] = useState(loadTheme);
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => storageBool(SIDEBAR_COLLAPSED_KEY));
  const [showCancelled, setShowCancelledState] = useState(() => storageBool(GLOBAL_CANCEL_KEY));
  const [catalog, setCatalog] = useState({ categories: [], workflows: [] });
  const [selectedId, setSelectedId] = useState(workflowFromUrl());
  const [workflow, setWorkflow] = useState(null);
  const [parameters, setParameters] = useState({});
  const [parameterLabels, setParameterLabels] = useState({});
  const [result, setResult] = useState(null);
  const [serverStatus, setServerStatus] = useState({ text: "Loading catalog…" });
  const [runStatus, setRunStatus] = useState({ text: "" });
  const [running, setRunning] = useState(false);
  const [documentCount, setDocumentCount] = useState(null);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);
  const [drawer, setDrawer] = useState(null);
  const showsDataModelGuide = workflow?.workflow_id === "data_model.guide";

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    setStorageBool(SIDEBAR_COLLAPSED_KEY, collapsed);
  }, [collapsed]);

  useEffect(() => {
    setStorageBool(GLOBAL_CANCEL_KEY, showCancelled);
  }, [showCancelled]);

  useEffect(() => {
    let alive = true;
    getCatalog()
      .then((payload) => {
        if (!alive) return;
        setCatalog(payload);
        setServerStatus({ text: "Connected", tone: "ok" });
        setSelectedId((current) => current || payload.workflows?.find((item) => !item.dev_only)?.workflow_id || null);
      })
      .catch((error) => {
        if (alive) setServerStatus({ text: `× ${error.message}`, tone: "err" });
      });
    getDisclaimer()
      .then((payload) => alive && setDocumentCount(payload.document_count))
      .catch(() => alive && setDocumentCount(null));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let alive = true;
    syncWorkflowToUrl(selectedId);
    getWorkflow(selectedId)
      .then((payload) => {
        if (!alive) return;
        setWorkflow(payload);
        setParameters(initialParameters(payload, showCancelled));
        setParameterLabels({});
        setResult(null);
        setRunStatus({ text: "" });
      })
      .catch((error) => alive && setRunStatus({ text: `× ${error.message}`, tone: "err" }));
    return () => {
      alive = false;
    };
  }, [selectedId, showCancelled]);

  const setShowCancelled = (value) => {
    setShowCancelledState(value);
    setParameters((current) => (current.include_cancelled === undefined ? current : { ...current, include_cancelled: value }));
  };

  function setParameter(name, value, label) {
    setParameters((current) => ({ ...current, [name]: value }));
    if (label !== undefined) {
      setParameterLabels((current) => ({ ...current, [name]: label }));
    }
  }

  async function executeWorkflow() {
    if (!workflow) return;
    setRunning(true);
    setRunStatus({ text: "Running…" });
    try {
      const payload = await runWorkflow(workflow.workflow_id, collectRunParameters(parameters, workflow));
      setResult(payload);
      setRunStatus({ text: summarizeResult(payload), tone: "ok" });
    } catch (error) {
      setRunStatus({ text: `× ${error.message}`, tone: "err" });
    } finally {
      setRunning(false);
    }
  }

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

  return (
    <>
      <DisclaimerOverlay open={disclaimerOpen} count={documentCount} onClose={() => setDisclaimerOpen(false)} />
      <Sidebar
        catalog={catalog}
        collapsed={collapsed}
        selected={selectedId}
        status={serverStatus}
        onSelect={setSelectedId}
        onToggle={() => setCollapsed(!collapsed)}
      />
      <main>
        <TopActions
          menuOpen={menuOpen}
          setMenuOpen={setMenuOpen}
          showCancelled={showCancelled}
          theme={theme}
          setShowCancelled={setShowCancelled}
          onOpenDisclaimer={() => {
            setMenuOpen(false);
            setDisclaimerOpen(true);
          }}
          onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        <div id="content">
          {showsDataModelGuide ? <DataModelGuide workflow={workflow} /> : <WorkflowHeader workflow={workflow} />}
          {workflow && !showsDataModelGuide ? (
            <WorkflowForm
              labels={parameterLabels}
              parameters={parameters}
              running={running}
              showCancelled={showCancelled}
              status={runStatus}
              workflow={workflow}
              setParameter={setParameter}
              onRun={executeWorkflow}
            />
          ) : null}
          {showsDataModelGuide ? null : (
            <WorkflowResults
              result={result}
              onEvidence={openEvidence}
              onSources={(sources, context) => setDrawer({ title: "Sources", subtitle: context, sources })}
            />
          )}
        </div>
      </main>
      <DocumentSourceDrawer
        drawer={drawer}
        onBack={() => setDrawer((current) => current ? { ...current, document: null, error: "" } : null)}
        onClose={() => setDrawer(null)}
        onOpenDocument={openDocument}
      />
    </>
  );
}
