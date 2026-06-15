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
  const showsDataModelGuide = workflow?.workflow_id === "data_model.guide";

  useEffect(() => {
    document.body.classList.remove("agent-sidebar-collapsed");
    document.body.classList.toggle("workflow-sidebar-collapsed", collapsed);
    return () => document.body.classList.remove("workflow-sidebar-collapsed");
  }, [collapsed]);

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
        drawer={drawer}
        onBack={backToSources}
        onClose={closeDrawer}
        onOpenDocument={openDocument}
      />
    </>
  );
}
