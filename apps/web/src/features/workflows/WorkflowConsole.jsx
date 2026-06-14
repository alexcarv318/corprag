import { useState } from "react";

import { DataModelGuide } from "../dataModel/DataModelGuide.jsx";
import DocumentSourceDrawer from "../documents/DocumentSourceDrawer.jsx";
import DisclaimerOverlay from "../shell/DisclaimerOverlay.jsx";
import Sidebar from "../shell/Sidebar.jsx";
import TopActions from "../shell/TopActions.jsx";
import { useAppPreferences } from "../../hooks/useAppPreferences.js";
import { useSourceDrawer } from "../../hooks/useSourceDrawer.js";
import { useWorkflowSession } from "../../hooks/useWorkflowSession.js";
import WorkflowForm from "./WorkflowForm.jsx";
import WorkflowHeader from "./WorkflowHeader.jsx";
import WorkflowResults from "./WorkflowResults.jsx";

export default function WorkflowConsole() {
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
    serverStatus,
    runStatus,
    running,
    documentCount,
    setParameter,
    setShowCancelled: updateShowCancelled,
    executeWorkflow
  } = useWorkflowSession({ showCancelled, setShowCancelled });
  const { drawer, openDocument, openEvidence, openSources, closeDrawer, backToSources } = useSourceDrawer();
  const showsDataModelGuide = workflow?.workflow_id === "data_model.guide";

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
          setShowCancelled={updateShowCancelled}
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
