import {
  ApiError,
  apiFetch,
  clearAuthSession,
  getAuthSession,
  setAuthSession
} from "./client.js";

export function isAuthError(error) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export async function signIn(username, password) {
  const payload = await apiFetch("/api/auth/sign-in", {
    method: "POST",
    body: JSON.stringify({ username: username.trim(), password }),
    suppressAuthExpired: true
  });
  setAuthSession({ user: payload.user, accessToken: payload.access_token });
  return payload.user;
}

export async function signUp({ username, password, signupKey }) {
  await apiFetch("/api/auth/sign-up", {
    method: "POST",
    body: JSON.stringify({
      username: username.trim(),
      password,
      signup_key: signupKey
    }),
    suppressAuthExpired: true
  });
  return signIn(username, password);
}

export async function verifyStoredSession() {
  const session = getAuthSession();
  if (!session?.accessToken) return null;
  try {
    const user = await apiFetch("/api/auth/me", { suppressAuthExpired: true });
    setAuthSession({ user, accessToken: session.accessToken });
    return user;
  } catch (error) {
    if (isAuthError(error)) {
      clearAuthSession();
      return null;
    }
    throw error;
  }
}

export function signOut() {
  apiFetch("/api/auth/sign-out", {
    method: "POST",
    suppressAuthExpired: true
  }).catch(() => {});
  clearAuthSession();
}
