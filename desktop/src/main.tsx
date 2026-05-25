import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Sync the `dark` class on <html> with the OS color-scheme preference.
// Done synchronously before React mounts to avoid a flash on dark systems.
const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");
function syncTheme(isDark: boolean) {
  document.documentElement.classList.toggle("dark", isDark);
}
syncTheme(colorScheme.matches);
colorScheme.addEventListener("change", (e) => syncTheme(e.matches));

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
