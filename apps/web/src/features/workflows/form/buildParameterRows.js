import {
  isPairedOrganizationParameter,
  pairedFieldLabel,
  workflowPairingFlags,
} from "./parameterUtils.js";

export function buildParameterRows(workflow) {
  const pairing = workflowPairingFlags(workflow);
  const parameterByName = new Map((workflow.parameters || []).map((parameter) => [parameter.name, parameter]));
  const since = parameterByName.get("since");
  const until = parameterByName.get("until");
  const limit = parameterByName.get("limit");

  const rows = [];
  const state = {
    dateRangeEmitted: false,
    subjectPairEmitted: false,
    fileKeywordEmitted: false,
    pairedParameters: {},
  };

  function emitDateRange() {
    if (state.dateRangeEmitted || !since || !until) return false;
    state.dateRangeEmitted = true;
    rows.push({ type: "date-range", key: "date-range", since, until, limit });
    return true;
  }

  function emitSubjectPair() {
    const subject = state.pairedParameters.subject_id;
    const organization = state.pairedParameters.participant_id
      || state.pairedParameters.organization_id
      || state.pairedParameters.involves_organization_id;
    if (state.subjectPairEmitted || !subject || !organization) return false;
    state.subjectPairEmitted = true;
    rows.push({
      type: "pair",
      key: "subject-organization-pair",
      left: subject,
      right: organization,
      leftLabel: pairedFieldLabel(subject),
      rightLabel: pairedFieldLabel(organization),
    });
    return true;
  }

  function emitFileKeywordPair() {
    const file = state.pairedParameters.file;
    const keyword = state.pairedParameters.q;
    if (state.fileKeywordEmitted || !file || !keyword) return false;
    state.fileKeywordEmitted = true;
    rows.push({ type: "pair", key: "file-keyword-pair", left: file, right: keyword });
    return true;
  }

  for (const parameter of workflow.parameters || []) {
    if (parameter.name === "event_domain") continue;

    if (pairing.pairFileKeyword && (parameter.name === "file" || parameter.name === "q")) {
      state.pairedParameters[parameter.name] = parameter;
      emitFileKeywordPair();
      continue;
    }

    if (
      (pairing.pairSubjectParticipant || pairing.pairSubjectOrganization)
      && (parameter.name === "subject_id" || isPairedOrganizationParameter(parameter.name))
    ) {
      state.pairedParameters[parameter.name] = parameter;
      emitSubjectPair();
      continue;
    }

    if (parameter.name === "event_type") {
      rows.push({ type: "full-width", key: parameter.name, parameter, variant: "event-type" });
      continue;
    }

    if (parameter.kind === "date" && (parameter.name === "since" || parameter.name === "until")) {
      continue;
    }

    if (parameter.name === "limit" && emitDateRange()) {
      continue;
    }

    if (parameter.kind === "boolean") {
      emitDateRange();
      rows.push({ type: "full-width", key: parameter.name, parameter, variant: "boolean" });
      continue;
    }

    rows.push({ type: "field", key: parameter.name, parameter });
  }

  emitDateRange();
  return rows;
}
