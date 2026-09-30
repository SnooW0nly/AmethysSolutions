// Simple global event bus to sync app actions across components (sidebar, overview, etc.)
// Events:
// - app-action-start: { appId: string, action: "start" | "stop" | "restart" }
// - app-action-end: { appId: string, action: "start" | "stop" | "restart" }
// - app-refetch: { appId: string }

type Action = "start" | "stop" | "restart";

class AppActionBus extends EventTarget {
  emitActionStart(appId: string, action: Action) {
    this.dispatchEvent(new CustomEvent("app-action-start", { detail: { appId, action } }));
  }
  emitActionEnd(appId: string, action: Action) {
    this.dispatchEvent(new CustomEvent("app-action-end", { detail: { appId, action } }));
  }
  emitRefetch(appId: string) {
    this.dispatchEvent(new CustomEvent("app-refetch", { detail: { appId } }));
  }
}

export const actionBus = new AppActionBus();


