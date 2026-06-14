import { WORKFLOW_ICONS } from "./workflowConstants.js";
import { workflowIconKey } from "./workflowUtils.js";

export function WorkflowIcon({ workflow }) {
  return (
    <span
      className="workflow-icon"
      dangerouslySetInnerHTML={{ __html: WORKFLOW_ICONS[workflowIconKey(workflow)] || WORKFLOW_ICONS.data }}
    />
  );
}
