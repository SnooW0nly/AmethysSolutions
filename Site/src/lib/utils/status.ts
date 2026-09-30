// Status mapping helpers
export type HostingStatus = string | null | undefined;

export function getHostingStatusDisplay(status?: HostingStatus): { label: string; dotClass: string; animated?: boolean } {
  const normalized = (status || "").toString().trim().toLowerCase();
  if (!normalized) return { label: "Não encontrado", dotClass: "bg-gray-400" };
  if (["running", "online", "on", "active"].includes(normalized)) {
    return { label: "Online", dotClass: "bg-green-500/80" };
  }
  if (["restarting", "reiniciando"].includes(normalized)) {
    return { label: "Reiniciando", dotClass: "bg-yellow-500/80", animated: true };
  }
  if (["stopped", "offline", "off", "shutdown", "stopping", "erro", "error"].includes(normalized)) {
    return { label: "Offline", dotClass: "bg-red-500/80" };
  }
  return { label: "Não encontrado", dotClass: "bg-gray-400" };
}


