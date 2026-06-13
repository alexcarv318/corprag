import Disclaimer from "./Disclaimer.jsx";
import Navigation from "./Navigation.jsx";

export default function Layout({ children, documentCount, disclaimerLoading }) {
  return (
    <div className="app-shell">
      <Navigation />
      <main>
        <div className="workspace-header">
          <div>
            <p className="eyebrow">Workflow console</p>
            <h1>Corporate graph workflows</h1>
          </div>
          <Disclaimer documentCount={documentCount} loading={disclaimerLoading} />
        </div>
        {children}
      </main>
    </div>
  );
}
