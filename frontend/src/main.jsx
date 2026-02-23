import React from "react";
import { createRoot } from "react-dom/client";
import BackendMCP from "./BackendMCP";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BackendMCP />
  </React.StrictMode>
);
