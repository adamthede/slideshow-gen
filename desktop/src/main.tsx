import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Dark-first (design-pass move #1): Marquee defaults to the warm dark
// palette. Light is the alternate, applied only when the OS *explicitly*
// prefers light. Done synchronously before React mounts to avoid a flash.
const lightScheme = window.matchMedia("(prefers-color-scheme: light)");
function syncTheme(prefersLight: boolean) {
  document.documentElement.classList.toggle("dark", !prefersLight);
}
const onColorSchemeChange = (e: MediaQueryListEvent) => syncTheme(e.matches);
syncTheme(lightScheme.matches);
lightScheme.addEventListener("change", onColorSchemeChange);
// Vite HMR re-evaluates this module on every save. Without cleanup, we
// accumulate listeners and each OS theme change fires N times.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    lightScheme.removeEventListener("change", onColorSchemeChange);
  });
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
