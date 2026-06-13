import { apiFetch, toQueryString } from "./client.js";

export function getDocumentSource(file) {
  return apiFetch(`/api/documents/source${toQueryString({ file })}`);
}

export function getDocumentTitles(files) {
  return apiFetch(`/api/documents/titles${toQueryString({ file: files })}`);
}
