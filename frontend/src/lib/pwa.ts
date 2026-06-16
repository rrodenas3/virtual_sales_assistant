export async function registerServiceWorker(): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  if (import.meta.env.VITE_PWA_ENABLED === "false") return;
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_SW_IN_DEV !== "true") {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
    return;
  }
  try {
    await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch (error) {
    console.warn("PHANTOM service worker registration failed", error);
  }
}
