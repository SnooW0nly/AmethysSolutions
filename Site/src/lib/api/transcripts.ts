// Camada de API para transcripts no frontend

export interface TranscriptMeta {
  publicId: string;
  channelName: string;
  channelId: string;
  guildName: string | null;
  guildId: string | null;
  ticketId: string | null;
  messageCount: number;
  participantCount: number;
  generatedBy: {
    userId: string | null;
    username: string | null;
    avatar: string | null;
  };
  views: number;
  createdAt: string;
  expiresAt: string;
}

async function handleJson<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error: any = new Error((data as any)?.error || `Request failed (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return data as T;
}

/**
 * Busca os metadados de um transcript pelo ID público
 */
export async function getTranscriptMeta(id: string): Promise<{ transcript: TranscriptMeta }> {
  const res = await fetch(`/api/v1/transcript/${id}`, {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  return handleJson(res);
}

/**
 * Retorna a URL do HTML do transcript (para iframe)
 */
export function getTranscriptHtmlUrl(id: string): string {
  return `/api/v1/transcript/${id}/html`;
}