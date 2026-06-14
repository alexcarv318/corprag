export default function TopActions({
  theme,
  onThemeToggle,
  menuOpen,
  setMenuOpen,
  showCancelled,
  setShowCancelled,
  onOpenDisclaimer,
  user,
  onSignOut,
  primaryLink = { href: "/agent", label: "Agent", title: "Open the Corprag agent" },
  showWorkflowSettings = true
}) {
  const initial = (user?.username || "?").slice(0, 1).toUpperCase();

  return (
    <div className="top-actions" aria-label="Page actions">
      <a className="top-agent-link" href={primaryLink.href} target="_self" rel="noopener noreferrer" title={primaryLink.title}>
        {primaryLink.label}
      </a>
      <button id="theme-toggle" className="top-icon-btn" type="button" title={`Theme: ${theme}`} aria-label={`Theme: ${theme}`} onClick={onThemeToggle}>
        <svg className="theme-icon-sun" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></svg>
        <svg className="theme-icon-moon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401" /></svg>
        <span className="sr-only">Toggle theme</span>
      </button>
      <div className="avatar-menu-wrap">
        <button id="avatar-menu-btn" className="avatar-btn" type="button" aria-label="Open account menu" aria-controls="avatar-menu" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          {initial}
        </button>
        <div id="avatar-menu" className="avatar-menu" hidden={!menuOpen}>
          <div className="menu-section account-summary">
            <span className="account-label">Signed in</span>
            <strong>{user?.username}</strong>
          </div>
          {showWorkflowSettings ? (
            <div className="menu-section">
              <label className="menu-switch" title="Also show items that are no longer in force across every workflow.">
                <span>Show inactive</span>
                <input id="global-show-cancelled" type="checkbox" checked={showCancelled} onChange={(event) => setShowCancelled(event.target.checked)} />
              </label>
              <label className="menu-switch" title="Show authority labels for row sources. Sorting still uses authority.">
                <span>Show source authority</span>
                <input id="global-show-source-authority" type="checkbox" defaultChecked />
              </label>
            </div>
          ) : null}
          <div className="menu-section">
            {onOpenDisclaimer ? (
              <button id="disclaimer-open-btn" className="menu-item" type="button" onClick={onOpenDisclaimer}>
                About this console
              </button>
            ) : null}
            <button id="logout-btn" className="menu-item" type="button" title="Sign out of workflows" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
