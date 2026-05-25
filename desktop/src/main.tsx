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
const onColorSchemeChange = (e: MediaQueryListEvent) => syncTheme(e.matches);
syncTheme(colorScheme.matches);
colorScheme.addEventListener("change", onColorSchemeChange);
// Vite HMR re-evaluates this module on every save. Without cleanup, we
// accumulate listeners and each OS theme change fires N times.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    colorScheme.removeEventListener("change", onColorSchemeChange);
  });
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
