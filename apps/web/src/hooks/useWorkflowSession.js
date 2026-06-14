import { useEffect, useState } from "react";

import { getCatalog, getDisclaimer, getWorkflow, runWorkflow } from "../api/workflows.js";
import { collectRunParameters, initialParameters } from "../features/workflows/form/parameterUtils.js";
import { summarizeResult } from "../features/workflows/shared/resultUtils.js";
import { workflowFromUrl, syncWorkflowToUrl } from "../utils/queryString.js";

export function useWorkflowSession({ showCancelled, setShowCancelled }) {
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

  function updateShowCancelled(value) {
    setShowCancelled(value);
    setParameters((current) => (current.include_cancelled === undefined ? current : { ...current, include_cancelled: value }));
  }

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

  return {
    catalog,
    selectedId,
    setSelectedId,
    workflow,
    parameters,
    parameterLabels,
    result,
    serverStatus,
    runStatus,
    running,
    documentCount,
    setParameter,
    setShowCancelled: updateShowCancelled,
    executeWorkflow
  };
}
