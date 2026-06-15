import { useEffect, useState } from "react";

import { DataModelGuide } from "../dataModel/DataModelGuide.jsx";
import DocumentSourceDrawer from "../documents/DocumentSourceDrawer.jsx";
import DisclaimerOverlay from "../shell/DisclaimerOverlay.jsx";
import Sidebar from "../shell/Sidebar.jsx";
import TopActions from "../shell/TopActions.jsx";
import { useAppPreferences } from "../../hooks/useAppPreferences.js";
import { useSourceDrawer } from "../../hooks/useSourceDrawer.js";
import { useWorkflowSession } from "../../hooks/useWorkflowSession.js";
import WorkflowForm from "./form/WorkflowForm.jsx";
import WorkflowHeader from "./WorkflowHeader.jsx";
import WorkflowResults from "./results/WorkflowResults.jsx";

export default function WorkflowConsole({ user, onSignOut }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);
  const { theme, setTheme, collapsed, setCollapsed, showCancelled, setShowCancelled } = useAppPreferences();
  const {
    catalog,
    selectedId,
    setSelectedId,
    workflow,
    parameters,
    parameterLabels,
    result,
    runStatus,
    running,
    documentCount,
    setParameter,
    setShowCancelled: updateShowCancelled,
    executeWorkflow
  } = useWorkflowSession({ showCancelled, setShowCancelled });
  const { drawer, openDocument, openEvidence, openSources, closeDrawer, backToSources } = useSourceDrawer();
  const [sourceLayoutState, setSourceLayoutState] = useState("closed");
  const showsDataModelGuide = workflow?.workflow_id === "data_model.guide";

  useEffect(() => {
    document.body.classList.remove("agent-sidebar-collapsed");
    document.body.classList.remove("agent-sources-open");
    document.body.classList.toggle("workflow-sidebar-collapsed", collapsed);
    return () => document.body.classList.remove("workflow-sidebar-collapsed");
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
    document.body.classList.toggle("workflow-sources-open", sourceLayoutState === "open");
    document.body.classList.toggle("workflow-sources-opening", sourceLayoutState === "opening");
    document.body.classList.toggle("workflow-sources-closing", sourceLayoutState === "closing");
    return () => {
      document.body.classList.remove("workflow-sources-open");
      document.body.classList.remove("workflow-sources-opening");
      document.body.classList.remove("workflow-sources-closing");
    };
  }, [sourceLayoutState]);

  return (
    <>
      <DisclaimerOverlay open={disclaimerOpen} count={documentCount} onClose={() => setDisclaimerOpen(false)} />
      <Sidebar
        catalog={catalog}
        collapsed={collapsed}
        selected={selectedId}
        onSelect={setSelectedId}
        onToggle={() => setCollapsed(!collapsed)}
      />
      <main>
        <TopActions
          menuOpen={menuOpen}
          setMenuOpen={setMenuOpen}
          showCancelled={showCancelled}
          theme={theme}
          setShowCancelled={updateShowCancelled}
          onOpenDisclaimer={() => {
            setMenuOpen(false);
            setDisclaimerOpen(true);
          }}
          onThemeToggle={() => setTheme(theme === "dark" ? "light" : "dark")}
          user={user}
          onSignOut={onSignOut}
        />
        <div id="content">
          {showsDataModelGuide ? <DataModelGuide workflow={workflow} /> : <WorkflowHeader workflow={workflow} />}
          {workflow && !showsDataModelGuide ? (
            <WorkflowForm
              labels={parameterLabels}
              parameters={parameters}
              running={running}
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
              onSources={openSources}
            />
          )}
        </div>
      </main>
      <DocumentSourceDrawer
        className="workflow-sources-drawer"
        drawer={drawer}
        onBack={backToSources}
        onClose={closeDrawer}
        onOpenDocument={openDocument}
      />
    </>
  );
}
