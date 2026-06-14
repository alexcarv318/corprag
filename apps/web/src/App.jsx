import { useEffect, useState } from "react";

import { signOut, verifyStoredSession } from "./api/auth.js";
import AgentPage from "./features/agent/AgentPage.jsx";
import SignInView from "./features/auth/SignInView.jsx";
import WorkflowConsole from "./features/workflows/WorkflowConsole.jsx";

export default function App() {
  const [authState, setAuthState] = useState({ status: "loading", user: null });

  useEffect(() => {
    let alive = true;
    verifyStoredSession()
      .then((user) => {
        if (!alive) return;
        setAuthState(user ? { status: "authenticated", user } : { status: "anonymous", user: null });
      })
      .catch(() => {
        if (alive) setAuthState({ status: "anonymous", user: null });
      });

    function handleExpired() {
      signOut();
      setAuthState({ status: "anonymous", user: null });
    }

    window.addEventListener("corporate-rag:auth-expired", handleExpired);
    return () => {
      alive = false;
      window.removeEventListener("corporate-rag:auth-expired", handleExpired);
    };
  }, []);

  function handleSignedIn(user) {
    setAuthState({ status: "authenticated", user });
  }

  function handleSignOut() {
    signOut();
    setAuthState({ status: "anonymous", user: null });
  }

  if (authState.status === "loading") {
    return <SessionLoadingView />;
  }

  if (authState.status === "anonymous") {
    return <SignInView onSignedIn={handleSignedIn} />;
  }

  if (window.location.pathname.startsWith("/agent")) {
    return (
      <AgentPage
        user={authState.user}
        onSignOut={handleSignOut}
        onOpenWorkflows={() => {
          window.location.href = "/";
        }}
      />
    );
  }

  return <WorkflowConsole user={authState.user} onSignOut={handleSignOut} />;
}

function SessionLoadingView() {
  return (
    <main className="session-loading-page" aria-busy="true" aria-live="polite">
      <div className="session-loading-panel">
        <div className="session-loading-spinner" aria-hidden="true" />
        <span>Checking session</span>
      </div>
    </main>
  );
}
