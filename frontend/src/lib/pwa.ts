export async function registerServiceWorker(): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  if (import.meta.env.VITE_PWA_ENABLED === "false") return;
  try {
    await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch (error) {
    console.warn("PHANTOM service worker registration failed", error);
  }
}
