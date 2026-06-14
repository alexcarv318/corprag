import { WORKFLOW_ICONS } from "./shared/workflowConstants.js";
import { workflowIconKey } from "./shared/workflowMeta.js";

export function WorkflowIcon({ workflow }) {
  return (
    <span
      className="workflow-icon"
      dangerouslySetInnerHTML={{ __html: WORKFLOW_ICONS[workflowIconKey(workflow)] || WORKFLOW_ICONS.data }}
    />
  );
}
