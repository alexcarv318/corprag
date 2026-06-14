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
  "phase_valid_from",
  "phase_valid_to"
]);

export const EVIDENCE_NUMBER_COLUMNS = new Set(["amount", "shares", "share_count", "total_shares", "nominal_value", "capital"]);

export const EVIDENCE_TEXT_COLUMNS = new Set([
  "registered_office",
  "registration_number",
  "address",
  "street",
  "passport",
  "residence",
  "nationality",
  "identifier"
]);

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
