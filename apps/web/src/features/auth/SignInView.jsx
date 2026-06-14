import { useState } from "react";

import { isAuthError, signIn, signUp } from "../../api/auth.js";

export default function SignInView({ loading, onSignedIn }) {
  const [mode, setMode] = useState("sign-in");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [signupKey, setSignupKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isSignUp = mode === "sign-up";

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = isSignUp
        ? await signUp({ username, password, signupKey })
        : await signIn(username, password);
      onSignedIn(user);
    } catch (caughtError) {
      setError(authErrorMessage(caughtError, isSignUp));
    } finally {
      setBusy(false);
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <main className="auth-page">
      <section className="signin-shell" aria-labelledby="signin-title">
        <form className="signin-panel" onSubmit={handleSubmit}>
          <div className="signin-copy">
            <h1 id="signin-title">{isSignUp ? "Create an account" : "Sign in to workflows"}</h1>
          </div>
          <label>
            <span>Username</span>
            <input
              autoComplete="username"
              autoFocus
              disabled={loading || busy}
              name="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label>
            <span>Password</span>
            <input
              autoComplete="current-password"
              disabled={loading || busy}
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {isSignUp ? (
            <label>
              <span>Invite key</span>
              <input
                autoComplete="off"
                disabled={loading || busy}
                name="signup-key"
                type="password"
                value={signupKey}
                onChange={(event) => setSignupKey(event.target.value)}
              />
            </label>
          ) : null}
          <button
            className="signin-submit"
            disabled={loading || busy || !username.trim() || !password || (isSignUp && !signupKey)}
            type="submit"
          >
            {submitLabel({ loading, busy, isSignUp })}
          </button>
          <p className="signin-error" role="alert">{error}</p>
          <div className="signin-mode-switch">
            {isSignUp ? (
              <button type="button" onClick={() => switchMode("sign-in")}>Use an existing account</button>
            ) : (
              <button type="button" onClick={() => switchMode("sign-up")}>Create account</button>
            )}
          </div>
        </form>
      </section>
    </main>
  );
}

function submitLabel({ loading, busy, isSignUp }) {
  if (loading) return "Checking session";
  if (busy) return isSignUp ? "Creating account" : "Signing in";
  return isSignUp ? "Create account" : "Sign in";
}

function authErrorMessage(error, isSignUp) {
  if (!isAuthError(error)) return error.message;
  if (isSignUp && error.status === 403) return "The invite key is not valid.";
  if (isSignUp && error.status === 409) return "That username already exists.";
  return "Wrong username or password.";
}
