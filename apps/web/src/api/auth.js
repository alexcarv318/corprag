import { ApiError } from "./client.js";

export function isAuthError(error) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}
