"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  Hash,
  ExternalLink,
  Maximize2,
  Minimize2,
  MessageSquare,
  Users,
  Eye,
  Calendar,
  User,
  Tag,
  Ticket,
  Clock,
  FileText,
  AlertCircle,
  Loader2,
  Shield,
} from "lucide-react";

interface TranscriptMeta {
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

function formatDate(dateStr: string) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getRemainingDays(expiresAt: string) {
  const now = new Date();
  const expires = new Date(expiresAt);
  const diffMs = expires.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "Expirado";
  if (diffDays === 1) return "Expira hoje";
  return `Expira em ${diffDays} dias`;
}

function getExpiryColor(expiresAt: string) {
  const now = new Date();
  const expires = new Date(expiresAt);
  const diffDays = Math.ceil((expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "var(--red)";
  if (diffDays <= 1) return "var(--orange)";
  return "var(--green)";
}

export default function TranscriptPage() {
  const params = useParams();
  const id = params?.id as string;

  const [meta, setMeta] = useState<TranscriptMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const fetchMeta = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/transcript/${id}`, { cache: "no-store" });
      if (res.status === 404) { setError("Transcript não encontrado ou expirado."); return; }
      if (!res.ok) throw new Error("Erro ao buscar transcript");
      const data = await res.json();
      setMeta(data.transcript);
    } catch {
      setError("Não foi possível carregar o transcript.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchMeta(); }, [fetchMeta]);

  const htmlUrl = `/api/v1/transcript/${id}/html`;
  const rawApiUrl = `${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/api/v1/transcript/${id}/html`;

  if (loading) return (
    <>
      <GlobalStyles />
      <div className="state-container">
        <div className="spinner-ring">
          <Loader2 size={28} className="spin-icon" />
        </div>
        <p className="state-label">Carregando transcript…</p>
      </div>
    </>
  );

  if (error) return (
    <>
      <GlobalStyles />
      <div className="state-container">
        <div className="error-icon-wrap">
          <AlertCircle size={36} />
        </div>
        <h2 className="error-title">Transcript indisponível</h2>
        <p className="error-desc">{error}</p>
        <p className="error-sub">Transcripts expiram automaticamente após alguns dias.</p>
      </div>
    </>
  );

  if (!meta) return null;

  const expiryColor = getExpiryColor(meta.expiresAt);

  return (
    <>
      <GlobalStyles />
      <div className={`page${fullscreen ? " page--fullscreen" : ""}`}>

        {/* ── Header ── */}
        {!fullscreen && (
          <header className="header">
            <div className="header-inner">
              <div className="brand">
                <span className="brand-dot" />
                <span className="brand-name">Amethys</span>
                <span className="brand-sep">/</span>
                <span className="brand-label">Transcript</span>
              </div>

              <div className="channel-pill">
                <Hash size={13} strokeWidth={2.5} />
                <span className="channel-name">{meta.channelName}</span>
                {meta.guildName && <span className="guild-name">{meta.guildName}</span>}
              </div>

              <div className="header-actions">
                <button className="btn btn--ghost" onClick={() => setFullscreen(true)}>
                  <Maximize2 size={14} />
                  <span>Expandir</span>
                </button>
                <a className="btn btn--primary" href={rawApiUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink size={14} />
                  <span>Abrir original</span>
                </a>
              </div>
            </div>
          </header>
        )}

        {/* ── Layout ── */}
        <div className={fullscreen ? "layout layout--fullscreen" : "layout"}>

          {/* ── Sidebar ── */}
          {!fullscreen && (
            <aside className="sidebar">

              {/* Channel card */}
              <div className="card">
                <div className="card-header">
                  <div className="card-icon-wrap">
                    <FileText size={16} />
                  </div>
                  <div>
                    <div className="card-title">
                      <Hash size={13} strokeWidth={2.5} />
                      {meta.channelName}
                    </div>
                    {meta.guildName && <div className="card-subtitle">{meta.guildName}</div>}
                  </div>
                </div>

                <div className="stat-grid">
                  <StatItem icon={<MessageSquare size={14} />} value={meta.messageCount || "—"} label="Mensagens" />
                  <StatItem icon={<Users size={14} />} value={meta.participantCount || "—"} label="Participantes" />
                  <StatItem icon={<Eye size={14} />} value={meta.views} label="Visualizações" />
                </div>
              </div>

              {/* Details card */}
              <div className="card">
                <h3 className="section-title">Detalhes</h3>

                <DetailRow icon={<Calendar size={13} />} label="Gerado em" value={formatDate(meta.createdAt)} />

                {meta.generatedBy.username && (
                  <div className="detail-row">
                    <span className="detail-label">
                      <User size={13} />
                      Por
                    </span>
                    <div className="generated-by">
                      {meta.generatedBy.avatar && (
                        <img src={meta.generatedBy.avatar} alt={meta.generatedBy.username} className="avatar" />
                      )}
                      <span className="detail-value">{meta.generatedBy.username}</span>
                    </div>
                  </div>
                )}

                <div className="detail-row">
                  <span className="detail-label">
                    <Tag size={13} />
                    ID público
                  </span>
                  <code className="code-chip">{meta.publicId}</code>
                </div>

                {meta.ticketId && (
                  <div className="detail-row">
                    <span className="detail-label">
                      <Ticket size={13} />
                      Ticket ID
                    </span>
                    <code className="code-chip">{meta.ticketId}</code>
                  </div>
                )}
              </div>

              {/* Expiry card */}
              <div className="card expiry-card" style={{ "--expiry-color": expiryColor } as React.CSSProperties}>
                <div className="expiry-icon">
                  <Clock size={16} />
                </div>
                <div>
                  <div className="expiry-status">{getRemainingDays(meta.expiresAt)}</div>
                  <div className="expiry-date">{formatDate(meta.expiresAt)}</div>
                </div>
              </div>

              {/* Disclaimer */}
              <div className="disclaimer">
                <Shield size={12} />
                <p>
                  Transcript gerado automaticamente pela Amethys. Removido automaticamente após a expiração.
                </p>
              </div>

            </aside>
          )}

          {/* ── Main iframe ── */}
          <main className={fullscreen ? "iframe-wrap iframe-wrap--fullscreen" : "iframe-wrap"}>
            {fullscreen && (
              <button className="btn btn--exit-fullscreen" onClick={() => setFullscreen(false)}>
                <Minimize2 size={15} />
                <span>Sair</span>
              </button>
            )}

            {!iframeLoaded && (
              <div className="iframe-loading">
                <Loader2 size={24} className="spin-icon" />
                <span>Carregando conversa…</span>
              </div>
            )}

            <iframe
              src={htmlUrl}
              className="iframe"
              style={{ opacity: iframeLoaded ? 1 : 0 }}
              onLoad={() => setIframeLoaded(true)}
              title={`Transcript #${meta.channelName}`}
              sandbox="allow-same-origin allow-scripts"
            />
          </main>
        </div>
      </div>
    </>
  );
}

/* ── Sub-components ── */
function StatItem({ icon, value, label }: { icon: React.ReactNode; value: number | string; label: string }) {
  return (
    <div className="stat-item">
      <span className="stat-icon">{icon}</span>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{icon}{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  );
}

/* ── Global Styles ── */
function GlobalStyles() {
  return (
    <style>{`
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

      :root {
        --bg:        #07080a;
        --surface:   #0e1014;
        --border:    rgba(255,255,255,0.07);
        --border-hi: rgba(255,255,255,0.12);
        --text:      #e2e8f0;
        --text-muted:#94a3b8;
        --text-dim:  rgba(255,255,255,0.3);
        --purple:    #9333ea;
        --purple-lo: rgba(147,51,234,0.15);
        --purple-hi: #c084fc;
        --red:       #ef4444;
        --orange:    #f97316;
        --green:     #22c55e;
        --radius:    12px;
        --sidebar-w: 272px;
        --header-h:  56px;
        --font:      'Inter', 'Segoe UI', system-ui, sans-serif;
        --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
      }

      body { background: var(--bg); color: var(--text); font-family: var(--font); -webkit-font-smoothing: antialiased; }

      /* ── Page ── */
      .page { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }
      .page--fullscreen { position: fixed; inset: 0; z-index: 9999; }

      /* ── Header ── */
      .header {
        height: var(--header-h);
        border-bottom: 1px solid var(--border);
        background: rgba(7,8,10,0.9);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        position: sticky; top: 0; z-index: 100;
      }
      .header-inner {
        max-width: 1440px; margin: 0 auto;
        padding: 0 20px; height: 100%;
        display: flex; align-items: center; gap: 16px;
      }

      /* brand */
      .brand { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
      .brand-dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--purple);
        box-shadow: 0 0 10px var(--purple);
      }
      .brand-name { font-size: 14px; font-weight: 700; color: #fff; letter-spacing: -.3px; }
      .brand-sep  { color: var(--text-dim); font-size: 14px; }
      .brand-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .6px; }

      /* channel pill */
      .channel-pill {
        display: flex; align-items: center; gap: 5px;
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--border);
        border-radius: 20px; padding: 4px 12px;
        flex: 1; min-width: 0; overflow: hidden;
        color: var(--text-muted);
      }
      .channel-pill svg { flex-shrink: 0; }
      .channel-name { font-size: 13px; font-weight: 600; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .guild-name   { font-size: 12px; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

      /* header actions */
      .header-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

      /* ── Buttons ── */
      .btn {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 7px 13px; border-radius: 8px;
        font-size: 13px; font-weight: 500; cursor: pointer;
        transition: background .15s, border-color .15s, color .15s;
        white-space: nowrap; text-decoration: none;
      }
      .btn--ghost {
        background: transparent;
        border: 1px solid var(--border);
        color: var(--text-muted);
      }
      .btn--ghost:hover { background: rgba(255,255,255,0.05); border-color: var(--border-hi); color: var(--text); }

      .btn--primary {
        background: var(--purple-lo);
        border: 1px solid rgba(147,51,234,0.3);
        color: var(--purple-hi);
      }
      .btn--primary:hover { background: rgba(147,51,234,0.25); border-color: rgba(147,51,234,0.5); }

      .btn--exit-fullscreen {
        position: absolute; top: 14px; right: 14px; z-index: 10;
        background: rgba(0,0,0,0.7); border: 1px solid var(--border-hi);
        color: var(--text-muted); backdrop-filter: blur(8px);
      }
      .btn--exit-fullscreen:hover { color: #fff; }

      /* ── Layout ── */
      .layout {
        display: flex; flex: 1;
        max-width: 1440px; width: 100%; margin: 0 auto;
        padding: 20px; gap: 20px; align-items: flex-start;
      }
      .layout--fullscreen { display: flex; flex: 1; height: 100%; padding: 0; }

      /* ── Sidebar ── */
      .sidebar {
        width: var(--sidebar-w); flex-shrink: 0;
        display: flex; flex-direction: column; gap: 12px;
        position: sticky; top: calc(var(--header-h) + 20px);
        animation: fadeUp .3s ease both;
      }

      /* ── Cards ── */
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 16px;
      }

      .card-header { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
      .card-icon-wrap {
        width: 34px; height: 34px; border-radius: 8px;
        background: var(--purple-lo); color: var(--purple-hi);
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        border: 1px solid rgba(147,51,234,0.2);
      }
      .card-title { display: flex; align-items: center; gap: 4px; font-size: 14px; font-weight: 600; color: #fff; }
      .card-subtitle { font-size: 11px; color: var(--text-dim); margin-top: 3px; }

      /* stats */
      .stat-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; }
      .stat-item {
        display: flex; flex-direction: column; align-items: center; gap: 4px;
        background: rgba(255,255,255,0.03); border: 1px solid var(--border);
        border-radius: 8px; padding: 10px 4px;
      }
      .stat-icon { color: var(--text-dim); }
      .stat-value { font-size: 17px; font-weight: 700; color: var(--purple-hi); line-height: 1; }
      .stat-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .4px; text-align: center; }

      /* section title */
      .section-title {
        font-size: 10px; font-weight: 600; color: var(--text-dim);
        text-transform: uppercase; letter-spacing: .8px; margin-bottom: 14px;
      }

      /* detail rows */
      .detail-row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
      .detail-row:last-child { margin-bottom: 0; }
      .detail-label {
        display: flex; align-items: center; gap: 5px;
        font-size: 10px; color: var(--text-dim);
        text-transform: uppercase; letter-spacing: .5px;
      }
      .detail-label svg { flex-shrink: 0; }
      .detail-value { font-size: 13px; color: var(--text-muted); font-weight: 500; padding-left: 18px; }

      .generated-by { display: flex; align-items: center; gap: 6px; padding-left: 18px; }
      .avatar { width: 18px; height: 18px; border-radius: 50%; }

      .code-chip {
        font-family: var(--font-mono); font-size: 11px;
        background: rgba(255,255,255,0.05);
        color: #a78bfa; padding: 3px 8px;
        border-radius: 5px; display: inline-block;
        margin-left: 18px; letter-spacing: .3px;
        border: 1px solid rgba(167,139,250,0.15);
      }

      /* expiry */
      .expiry-card { display: flex; align-items: center; gap: 12px; }
      .expiry-icon {
        width: 34px; height: 34px; border-radius: 8px; flex-shrink: 0;
        background: rgba(255,255,255,0.04); border: 1px solid var(--border);
        display: flex; align-items: center; justify-content: center;
        color: var(--expiry-color, var(--text-muted));
      }
      .expiry-status { font-size: 13px; font-weight: 600; color: var(--expiry-color, var(--text-muted)); }
      .expiry-date   { font-size: 11px; color: var(--text-dim); margin-top: 2px; }

      /* disclaimer */
      .disclaimer {
        display: flex; align-items: flex-start; gap: 8px;
        color: var(--text-dim); font-size: 11px; line-height: 1.6;
        padding: 0 2px;
      }
      .disclaimer svg { flex-shrink: 0; margin-top: 2px; }

      /* ── Iframe ── */
      .iframe-wrap {
        flex: 1; border-radius: var(--radius); overflow: hidden;
        border: 1px solid var(--border); background: #313338;
        min-height: calc(100vh - var(--header-h) - 40px);
        position: relative; display: flex; flex-direction: column;
        animation: fadeUp .4s .05s ease both;
      }
      .iframe-wrap--fullscreen {
        flex: 1; border-radius: 0; border: none;
        position: relative; display: flex; flex-direction: column;
        min-height: 0;
      }
      .iframe {
        width: 100%; flex: 1; border: none;
        min-height: calc(100vh - var(--header-h) - 40px);
        transition: opacity .3s ease;
      }
      .iframe-wrap--fullscreen .iframe { min-height: 0; height: 100%; }

      .iframe-loading {
        position: absolute; inset: 0; z-index: 1;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 12px; background: #313338; color: var(--text-muted); font-size: 13px;
      }

      /* ── States ── */
      .state-container {
        min-height: 100vh; background: var(--bg);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 12px; padding: 24px; text-align: center;
      }
      .spinner-ring {
        width: 52px; height: 52px; border-radius: 50%;
        background: var(--purple-lo); border: 1px solid rgba(147,51,234,0.2);
        display: flex; align-items: center; justify-content: center;
        color: var(--purple-hi);
      }
      .error-icon-wrap {
        width: 64px; height: 64px; border-radius: 16px;
        background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2);
        display: flex; align-items: center; justify-content: center;
        color: #ef4444; margin-bottom: 4px;
      }
      .state-label { color: var(--text-dim); font-size: 14px; }
      .error-title { font-size: 18px; font-weight: 700; color: #fff; }
      .error-desc  { font-size: 14px; color: var(--text-muted); }
      .error-sub   { font-size: 12px; color: var(--text-dim); max-width: 360px; }

      /* ── Animations ── */
      .spin-icon { animation: spin .8s linear infinite; }
      @keyframes spin    { to { transform: rotate(360deg); } }
      @keyframes fadeUp  { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

      /* ── Responsive ── */
      @media (max-width: 960px) {
        .layout { flex-direction: column; padding: 16px; gap: 16px; }
        .sidebar { width: 100%; position: static; }
        .stat-grid { grid-template-columns: repeat(3,1fr); }
        .iframe-wrap { min-height: 70vh; }
        .iframe { min-height: 70vh; }
        .guild-name { display: none; }
      }

      @media (max-width: 600px) {
        :root { --header-h: 52px; }
        .header-inner { padding: 0 14px; gap: 10px; }
        .brand-sep, .brand-label { display: none; }
        .channel-pill { padding: 4px 10px; }
        .btn span { display: none; }
        .btn { padding: 7px 10px; }
        .layout { padding: 12px; gap: 12px; }
        .card { padding: 14px; }
      }
    `}</style>
  );
}
