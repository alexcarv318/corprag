import { Bot, Workflow } from "lucide-react";

export default function Navigation() {
  return (
    <nav className="top-nav" aria-label="Primary navigation">
      <a className="brand" href="/workflows">
        <Workflow size={20} />
        <span>Corporate RAG</span>
      </a>
      <div className="nav-links">
        <a aria-current="page" href="/workflows">
          Workflows
        </a>
        <a href="/agent">
          <Bot size={16} />
          Agent
        </a>
      </div>
    </nav>
  );
}
