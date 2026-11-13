import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";
import "./design-system.css";
import "./customer-portal.css";
import "./partner-workspace.css";
import "./operations-workspace.css";
import "./warehouse-workspace.css";
import "./parcel-operations.css";
import "./parcel-operations.css";
import "./partner-workspace.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);