export const TYPEAHEAD_SUFFIX_MAP = [
  ["subject_id", "subject"],
  ["person_id", "person"],
  ["phase_id", "phase"],
  ["event_id", "event"],
  ["work_id", "work"],
  ["file", "file"],
  ["organization_id", "organization"],
  ["participant_id", "organization"],
  ["class_id", "class"],
  ["from_class_id", "class"],
  ["to_class_id", "class"],
  ["module", "module"]
];

export const TYPEAHEAD_LIMITS = {
  subject: 12,
  person: 12,
  organization: 12,
  file: 12,
  event: 10,
  phase: 10,
  work: 10,
  class: 12,
  module: 12
};

export const WORKFLOW_ICONS = {
  subject:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M6.70001 18H4.15002C2.72002 18 2 17.28 2 15.85V4.15002C2 2.72002 2.72002 2 4.15001 2H8.45001C9.88001 2 10.6 2.72002 10.6 4.15002V6" stroke="currentColor" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M17.3699 8.41998V19.58C17.3699 21.19 16.57 22 14.96 22H9.11993C7.50993 22 6.69995 21.19 6.69995 19.58V8.41998C6.69995 6.80998 7.50993 6 9.11993 6H14.96C16.57 6 17.3699 6.80998 17.3699 8.41998Z" stroke="currentColor" stroke-width="1.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 11H14M10 14H14M12 22V19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  organization:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M7 10.74V13.94M12 9V15.68M17 10.74V13.94" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  person:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M17 21H7C3 21 2 20 2 16V8C2 4 3 3 7 3H17C21 3 22 4 22 8V16C22 20 21 21 17 21Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 8H19M15 12H19M17 16H19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M8.49994 11.2899C9.49958 11.2899 10.3099 10.4796 10.3099 9.47992C10.3099 8.48029 9.49958 7.66992 8.49994 7.66992C7.50031 7.66992 6.68994 8.48029 6.68994 9.47992C6.68994 10.4796 7.50031 11.2899 8.49994 11.2899Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 16.33C11.86 14.88 10.71 13.74 9.26 13.61C8.76 13.56 8.25 13.56 7.74 13.61C6.29 13.75 5.14 14.88 5 16.33" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  document:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M22 10V15C22 20 20 22 15 22H9C4 22 2 20 2 15V9C2 4 4 2 9 2H14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 10H18C15 10 14 9 14 6V2L22 10Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 13H13M7 17H11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  capital:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M18.32 11.9999C20.92 11.9999 22 10.9999 21.04 7.71994C20.39 5.50994 18.49 3.60994 16.28 2.95994C13 1.99994 12 3.07994 12 5.67994V8.55994C12 10.9999 13 11.9999 15 11.9999H18.32Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M19.9999 14.7C19.0699 19.33 14.6299 22.69 9.57993 21.87C5.78993 21.26 2.73993 18.21 2.11993 14.42C1.30993 9.39001 4.64993 4.95001 9.25993 4.01001" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  poa:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M19 9C19 10.45 18.57 11.78 17.83 12.89C16.75 14.49 15.04 15.62 13.05 15.91C12.71 15.97 12.36 16 12 16C11.64 16 11.29 15.97 10.95 15.91C8.96 15.62 7.25 14.49 6.17 12.89C5.43 11.78 5 10.45 5 9C5 5.13 8.13 2 12 2C15.87 2 19 5.13 19 9Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M21.25 18.47L19.6 18.86C19.23 18.95 18.94 19.23 18.86 19.6L18.51 21.07C18.32 21.87 17.3 22.11 16.77 21.48L12 16L7.22996 21.49C6.69996 22.12 5.67996 21.88 5.48996 21.08L5.13996 19.61C5.04996 19.24 4.75996 18.95 4.39996 18.87L2.74996 18.48C1.98996 18.3 1.71996 17.35 2.26996 16.8L6.16996 12.9C7.24996 14.5 8.95996 15.63 10.95 15.92C11.29 15.98 11.64 16.01 12 16.01C12.36 16.01 12.71 15.98 13.05 15.92C15.04 15.63 16.75 14.5 17.83 12.9L21.73 16.8C22.28 17.34 22.01 18.29 21.25 18.47Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  event:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M15.24 2H8.76004C5.00004 2 4.71004 5.38 6.74004 7.22L17.26 16.78C19.29 18.62 19 22 15.24 22H8.76004C5.00004 22 4.71004 18.62 6.74004 16.78L17.26 7.22C19.29 5.38 19 2 15.24 2Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  data:
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><path d="M13.01 2.92007L18.91 5.54007C20.61 6.29007 20.61 7.53007 18.91 8.28007L13.01 10.9001C12.34 11.2001 11.24 11.2001 10.57 10.9001L4.67 8.28007C2.97 7.53007 2.97 6.29007 4.67 5.54007L10.57 2.92007C11.24 2.62007 12.34 2.62007 13.01 2.92007Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 11C3 11.84 3.63 12.81 4.4 13.15L11.19 16.17C11.71 16.4 12.3 16.4 12.81 16.17L19.6 13.15C20.37 12.81 21 11.84 21 11M3 16C3 16.93 3.55 17.77 4.4 18.15L11.19 21.17C11.71 21.4 12.3 21.4 12.81 21.17L19.6 18.15C20.45 17.77 21 16.93 21 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
};

export const DOCUMENT_TYPE_LABELS = {
  incorporation_certificate: "Incorporation certificate",
  articles_of_association_or_bylaws: "Articles of association",
  continuation_certificate: "Continuation certificate",
  discontinuance_certificate: "Discontinuance certificate",
  dissolution_certificate: "Dissolution certificate",
  registry_extract_certificate: "Registry extract certificate",
  registry_filing: "Registry filing",
  administrative_certificate: "Administrative certificate",
  good_standing_certificate: "Good standing certificate",
  board_resolution: "Board resolution",
  board_meeting_minutes: "Board meeting minutes",
  shareholder_resolution: "Shareholder resolution",
  shareholder_meeting_minutes: "Shareholder meeting minutes",
  director_appointment: "Director appointment",
  director_resignation: "Director resignation",
  director_resolution: "Director resolution",
  share_certificate: "Share certificate",
  share_register: "Share register",
  share_transfer_agreement: "Share transfer agreement",
  share_contribution_agreement: "Share contribution agreement",
  power_of_attorney: "Power of attorney",
  proxy: "Proxy",
  intercompany_or_other_agreement: "Agreement",
  banking_payment_or_credit_record: "Banking or payment record",
  annual_accounts_financial_statements: "Annual accounts",
  tax_document: "Tax document",
  legal_declaration: "Legal declaration",
  legal_opinion: "Legal opinion",
  corporate_data_sheet: "Corporate data sheet",
  registry_extract: "Registry extract",
  correspondence: "Correspondence",
  other: "Other document"
};

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
