export const EVIDENCE_DATE_COLUMNS = new Set([
  "date_of_incorporation",
  "date_of_dissolution",
  "date_of_birth",
  "effective_date",
  "as_of",
  "term_start",
  "term_end",
  "from",
  "to",
  "valid_from",
  "valid_to",
  "valid_until",
  "active_from",
  "active_until",
  "phase_valid_from",
  "phase_valid_to",
  "latest_certificate_date",
  "latest_good_standing_date"
]);

export const EVIDENCE_NUMBER_COLUMNS = new Set([
  "amount",
  "shares",
  "share_count",
  "number_of_shares",
  "total_shares",
  "nominal_value",
  "share_capital",
  "capital"
]);

export const EVIDENCE_TEXT_COLUMNS = new Set([
  "registered_offices",
  "registered_office",
  "registration_numbers",
  "registration_number",
  "address",
  "street",
  "passport",
  "residence",
  "nationality",
  "identifier",
  "tax_identifier",
  "bank_identifier",
  "certificate_identifier"
]);

export const EVIDENCE_DATE_SUFFIXES = [
  "_valid_from",
  "_valid_to",
  "_valid_until",
  "_from",
  "_to",
  "_until",
  "_date"
];

const NON_EVIDENCE_CELLS = new Set([
  "subject_phases:registered_office"
]);

export function isEvidenceCellDisabled(tableId, columnName) {
  if (!tableId || !columnName) return false;
  return NON_EVIDENCE_CELLS.has(`${tableId}:${columnName}`);
}

export const ALWAYS_HIDDEN_COLUMNS = new Set([
  "phase_classes",
  "fibo_classes",
  "work_lifecycle_status",
  "expression_lifecycle_status",
  "item_lifecycle_status",
  "legal_name_canonical",
  "edge_count",
  "source_doc",
  "source_chunk",
  "supporting_files",
  "mention_count",
  "_dev"
]);
