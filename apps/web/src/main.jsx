import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RecoilRoot } from "recoil";

import App from "./App.jsx";
import "./styles/workflows.css";
import "./styles/agent.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <RecoilRoot>
      <App />
    </RecoilRoot>
  </StrictMode>
);
