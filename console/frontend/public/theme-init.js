// Runs before the page draws, so a saved light or dark choice never flashes the other theme.
// "system" (or nothing saved) leaves the choice to prefers-color-scheme.
try {
  var saved = window.localStorage.getItem("cti-console-theme");
  if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
} catch (e) {
  // Storage blocked: follow the system theme.
}
