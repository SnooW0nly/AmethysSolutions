"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Search, Users, MessageSquare, Mic, Clock, ChevronLeft, ChevronRight, X, ArrowUpDown, Shield, Hash, Volume2, Edit3, Trash2, ChevronDown, ChevronUp, Globe, Bot } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MonitorUser {
  _id: string;
  profile: {
    current_username?: string;
    current_display_name?: string;
    current_avatar_url?: string;
    current_pronouns?: string;
  };
  meta: {
    first_seen?: string;
    last_seen?: string;
    last_updated?: string;
    total_messages?: number;
    total_voice_events?: number;
    seen_by_bots?: string[];
  };
  activity?: {
    guilds_seen?: Array<{
      guild_id: string;
      guild_name: string;
      first_seen: string;
      last_seen: string;
    }>;
    messages_sent?: Array<{
      message_id: string;
      guild_id: string;
      channel_id: string;
      content: string;
      timestamp: string;
    }>;
    messages_deleted?: Array<{
      message_id: string;
      guild_id: string;
      channel_id: string;
      content: string;
      deleted_at: string;
    }>;
    messages_edited?: Array<{
      message_id: string;
      before: string;
      after: string;
      edited_at: string;
    }>;
    voice_sessions?: Array<{
      guild_id: string;
      channel_id: string;
      action: string;
      timestamp: string;
    }>;
  };
  history?: {
    usernames?: Array<{ value: string; changed_at: string; bot: string }>;
    display_names?: Array<{ value: string; changed_at: string; bot: string }>;
    avatars?: Array<{ url: string; changed_at: string; bot: string }>;
    pronouns?: Array<{ value: string; changed_at: string; bot: string }>;
    nicknames?: Record<string, Array<{ value: string; changed_at: string; bot: string }>>;
  };
}

interface MonitorStats {
  totalUsers: number;
  totalMessages: number;
  totalVoiceEvents: number;
  lastActivity: string | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function fmtRelative(d?: string | null) {
  if (!d) return "—";
  const ms = Date.now() - new Date(d).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s atrás`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}

function getAvatar(user: MonitorUser) {
  const url = user.profile?.current_avatar_url;
  if (url && url.startsWith("http")) return url;
  // Generate Discord default avatar by user ID
  const id = BigInt(user._id);
  const idx = Number((id >> 22n) % 6n);
  return `https://cdn.discordapp.com/embed/avatars/${idx}.png`;
}

function actionLabel(action: string) {
  const map: Record<string, string> = {
    voice_join: "Entrou na call",
    voice_leave: "Saiu da call",
    voice_move: "Moveu de call",
    voice_mic_mute: "Mutou mic",
    voice_mic_unmute: "Desmutou mic",
    voice_deafen: "Ensurdeceu",
    voice_undeafen: "Desensurdeceu",
    voice_stream_start: "Iniciou stream",
    voice_stream_stop: "Parou stream",
    voice_cam_on: "Câmera ligada",
    voice_cam_off: "Câmera desligada",
    voice_server_mute: "Mutado pelo server",
    voice_server_unmute: "Desmutado pelo server",
  };
  return map[action] || action;
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-xl border border-foreground/10 bg-foreground/[0.03] p-4 flex items-center gap-3">
      <div className={`p-2.5 rounded-lg ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-foreground/50 font-medium">{label}</p>
        <p className="text-lg font-bold">{value}</p>
      </div>
    </div>
  );
}

// ─── User Row ─────────────────────────────────────────────────────────────────

function UserRow({ user, onClick }: { user: MonitorUser; onClick: () => void }) {
  const name = user.profile?.current_display_name || user.profile?.current_username || "Desconhecido";
  const username = user.profile?.current_username;
  const guilds = user.activity?.guilds_seen?.length || 0;

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-3 hover:bg-foreground/5 cursor-pointer transition-colors border-b border-foreground/5 last:border-0"
    >
      <img
        src={getAvatar(user)}
        alt={name}
        className="w-9 h-9 rounded-full flex-shrink-0 bg-foreground/10"
        onError={(e) => { (e.target as HTMLImageElement).src = "https://cdn.discordapp.com/embed/avatars/0.png"; }}
      />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm truncate">{name}</p>
        <p className="text-xs text-foreground/50 font-mono truncate">
          {username ? `@${username}` : ""} · {user._id}
        </p>
      </div>
      <div className="hidden md:flex items-center gap-4 text-xs text-foreground/50 flex-shrink-0">
        <span className="flex items-center gap-1">
          <MessageSquare className="w-3 h-3" />
          {(user.meta?.total_messages || 0).toLocaleString()}
        </span>
        <span className="flex items-center gap-1">
          <Mic className="w-3 h-3" />
          {(user.meta?.total_voice_events || 0).toLocaleString()}
        </span>
        <span className="flex items-center gap-1">
          <Globe className="w-3 h-3" />
          {guilds}
        </span>
        <span className="flex items-center gap-1 w-28 justify-end">
          <Clock className="w-3 h-3" />
          {fmtRelative(user.meta?.last_seen)}
        </span>
      </div>
    </div>
  );
}

// ─── Collapsible Section ──────────────────────────────────────────────────────

function Section({ title, icon: Icon, count, children }: { title: string; icon: any; count?: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-foreground/10 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-foreground/5 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Icon className="w-4 h-4 text-foreground/50" />
          {title}
          {count !== undefined && (
            <span className="text-xs bg-foreground/10 text-foreground/60 px-1.5 py-0.5 rounded-full">{count}</span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-foreground/40" /> : <ChevronDown className="w-4 h-4 text-foreground/40" />}
      </button>
      {open && <div className="border-t border-foreground/10 p-4">{children}</div>}
    </div>
  );
}

// ─── User Detail Modal ────────────────────────────────────────────────────────

function UserDetailModal({ userId, onClose }: { userId: string; onClose: () => void }) {
  const [user, setUser] = useState<MonitorUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/admin/monitor/users/${userId}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success) setUser(d.user);
        else setError(d.error || "Erro ao carregar");
      })
      .catch(() => setError("Erro de conexão"))
      .finally(() => setLoading(false));
  }, [userId]);

  const name = user?.profile?.current_display_name || user?.profile?.current_username || userId;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl bg-background border border-foreground/10 rounded-2xl shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-foreground/10">
          <h2 className="font-bold text-base">Perfil do Usuário</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-foreground/10 rounded-lg transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          {loading && (
            <div className="flex items-center justify-center py-16 text-foreground/40 text-sm">
              Carregando...
            </div>
          )}

          {error && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm p-3">
              {error}
            </div>
          )}

          {user && !loading && (
            <div className="space-y-4">
              {/* Profile header */}
              <div className="flex items-start gap-4">
                <img
                  src={getAvatar(user)}
                  alt={name}
                  className="w-16 h-16 rounded-2xl bg-foreground/10 flex-shrink-0"
                  onError={(e) => { (e.target as HTMLImageElement).src = "https://cdn.discordapp.com/embed/avatars/0.png"; }}
                />
                <div className="flex-1 min-w-0">
                  <h3 className="text-xl font-bold truncate">{name}</h3>
                  {user.profile?.current_username && (
                    <p className="text-sm text-foreground/50">@{user.profile.current_username}</p>
                  )}
                  {user.profile?.current_pronouns && (
                    <p className="text-xs text-foreground/40 mt-0.5">{user.profile.current_pronouns}</p>
                  )}
                  <p className="text-xs font-mono text-foreground/30 mt-1">{user._id}</p>
                </div>
              </div>

              {/* Quick stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div className="bg-foreground/[0.04] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold">{(user.meta?.total_messages || 0).toLocaleString()}</p>
                  <p className="text-xs text-foreground/50">Mensagens</p>
                </div>
                <div className="bg-foreground/[0.04] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold">{(user.meta?.total_voice_events || 0).toLocaleString()}</p>
                  <p className="text-xs text-foreground/50">Eventos de voz</p>
                </div>
                <div className="bg-foreground/[0.04] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold">{user.activity?.guilds_seen?.length || 0}</p>
                  <p className="text-xs text-foreground/50">Servidores</p>
                </div>
                <div className="bg-foreground/[0.04] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold">{user.meta?.seen_by_bots?.length || 0}</p>
                  <p className="text-xs text-foreground/50">Bots</p>
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-foreground/[0.03] rounded-lg p-2.5">
                  <p className="text-foreground/40 mb-0.5">Primeiro visto</p>
                  <p className="font-medium">{fmtDate(user.meta?.first_seen)}</p>
                </div>
                <div className="bg-foreground/[0.03] rounded-lg p-2.5">
                  <p className="text-foreground/40 mb-0.5">Último visto</p>
                  <p className="font-medium">{fmtDate(user.meta?.last_seen)}</p>
                </div>
              </div>

              {/* Bots que viram este usuário */}
              {user.meta?.seen_by_bots && user.meta.seen_by_bots.length > 0 && (
                <Section title="Bots que rastrearam" icon={Bot} count={user.meta.seen_by_bots.length}>
                  <div className="flex flex-wrap gap-2">
                    {user.meta.seen_by_bots.map((bot) => (
                      <span key={bot} className="text-xs bg-foreground/10 px-2 py-1 rounded-full font-mono">{bot}</span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Guilds */}
              {user.activity?.guilds_seen && user.activity.guilds_seen.length > 0 && (
                <Section title="Servidores vistos" icon={Globe} count={user.activity.guilds_seen.length}>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {user.activity.guilds_seen.map((g) => (
                      <div key={g.guild_id} className="flex items-center justify-between text-xs py-1 border-b border-foreground/5 last:border-0">
                        <div>
                          <p className="font-semibold">{g.guild_name}</p>
                          <p className="text-foreground/40 font-mono">{g.guild_id}</p>
                        </div>
                        <p className="text-foreground/40 text-right">
                          Visto {fmtRelative(g.last_seen)}
                        </p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Username history */}
              {user.history?.usernames && user.history.usernames.length > 0 && (
                <Section title="Histórico de usernames" icon={Hash} count={user.history.usernames.length}>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto">
                    {[...user.history.usernames].reverse().map((h, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="font-mono font-medium">@{h.value}</span>
                        <span className="text-foreground/40">{fmtDate(h.changed_at)}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Display name history */}
              {user.history?.display_names && user.history.display_names.length > 0 && (
                <Section title="Histórico de nomes de exibição" icon={Hash} count={user.history.display_names.length}>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto">
                    {[...user.history.display_names].reverse().map((h, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="font-medium">{h.value}</span>
                        <span className="text-foreground/40">{fmtDate(h.changed_at)}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Avatar history */}
              {user.history?.avatars && user.history.avatars.length > 0 && (
                <Section title="Histórico de avatares" icon={Shield} count={user.history.avatars.length}>
                  <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                    {[...user.history.avatars].reverse().slice(0, 20).map((a, i) => (
                      <div key={i} className="text-center">
                        <img
                          src={a.url}
                          alt="avatar"
                          className="w-12 h-12 rounded-lg bg-foreground/10 object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                        <p className="text-[10px] text-foreground/30 mt-0.5">{fmtRelative(a.changed_at)}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Últimas mensagens */}
              {user.activity?.messages_sent && user.activity.messages_sent.length > 0 && (
                <Section title="Últimas mensagens enviadas" icon={MessageSquare} count={user.activity.messages_sent.length}>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {[...user.activity.messages_sent].reverse().slice(0, 30).map((m, i) => (
                      <div key={i} className="bg-foreground/[0.03] rounded-lg p-2.5 text-xs">
                        <p className="text-foreground/40 mb-1 font-mono">
                          #{m.channel_id} · {fmtRelative(m.timestamp)}
                        </p>
                        <p className="break-words">{m.content || "(sem conteúdo)"}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Mensagens deletadas */}
              {user.activity?.messages_deleted && user.activity.messages_deleted.length > 0 && (
                <Section title="Mensagens deletadas" icon={Trash2} count={user.activity.messages_deleted.length}>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {[...user.activity.messages_deleted].reverse().slice(0, 20).map((m, i) => (
                      <div key={i} className="bg-red-500/5 border border-red-500/10 rounded-lg p-2.5 text-xs">
                        <p className="text-foreground/40 mb-1 font-mono">
                          #{m.channel_id} · deletado {fmtRelative(m.deleted_at)}
                        </p>
                        <p className="break-words text-red-400/80">{m.content || "(sem conteúdo)"}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Mensagens editadas */}
              {user.activity?.messages_edited && user.activity.messages_edited.length > 0 && (
                <Section title="Mensagens editadas" icon={Edit3} count={user.activity.messages_edited.length}>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {[...user.activity.messages_edited].reverse().slice(0, 20).map((m, i) => (
                      <div key={i} className="bg-yellow-500/5 border border-yellow-500/10 rounded-lg p-2.5 text-xs space-y-1">
                        <p className="text-foreground/40 font-mono">editado {fmtRelative(m.edited_at)}</p>
                        <p className="line-through text-foreground/40">{m.before || "(vazio)"}</p>
                        <p className="text-foreground/90">{m.after || "(vazio)"}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              )}

              {/* Sessões de voz */}
              {user.activity?.voice_sessions && user.activity.voice_sessions.length > 0 && (
                <Section title="Sessões de voz" icon={Volume2} count={user.activity.voice_sessions.length}>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {[...user.activity.voice_sessions].reverse().slice(0, 30).map((v, i) => (
                      <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-foreground/5 last:border-0">
                        <span className="font-medium">{actionLabel(v.action)}</span>
                        <span className="text-foreground/40 font-mono">{fmtRelative(v.timestamp)}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function MonitorSection() {
  const [users, setUsers] = useState<MonitorUser[]>([]);
  const [stats, setStats] = useState<MonitorStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [sort, setSort] = useState("last_seen");
  const [order, setOrder] = useState("desc");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (q: string, pg: number, s: string, o: string) => {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ q, page: String(pg), limit: "20", sort: s, order: o });
      const res = await fetch(`/api/admin/monitor/users?${qs}`);
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || "Erro ao buscar usuários");
      setUsers(data.users || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load stats once
  useEffect(() => {
    setStatsLoading(true);
    fetch("/api/admin/monitor/stats")
      .then((r) => r.json())
      .then((d) => { if (d.success) setStats(d.stats); })
      .catch(() => {})
      .finally(() => setStatsLoading(false));
  }, []);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      load(search, 1, sort, order);
    }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search, sort, order]);

  // Page change
  useEffect(() => {
    load(search, page, sort, order);
  }, [page]);

  const toggleSort = (field: string) => {
    if (sort === field) {
      setOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSort(field);
      setOrder("desc");
    }
    setPage(1);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Stats */}
      {!statsLoading && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard icon={Users} label="Usuários monitorados" value={stats.totalUsers.toLocaleString()} color="bg-blue-500/15 text-blue-400" />
          <StatCard icon={MessageSquare} label="Total de mensagens" value={stats.totalMessages.toLocaleString()} color="bg-green-500/15 text-green-400" />
          <StatCard icon={Mic} label="Eventos de voz" value={stats.totalVoiceEvents.toLocaleString()} color="bg-purple-500/15 text-purple-400" />
          <StatCard icon={Clock} label="Última atividade" value={fmtRelative(stats.lastActivity)} color="bg-orange-500/15 text-orange-400" />
        </div>
      )}

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/40 pointer-events-none" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nome, username ou Discord ID..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-foreground/5 border border-foreground/10 rounded-xl outline-none focus:border-foreground/30 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/40 hover:text-foreground/70">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex gap-1">
          {[
            { key: "last_seen", label: "Visto" },
            { key: "total_messages", label: "Msgs" },
            { key: "first_seen", label: "Descoberto" },
          ].map((s) => (
            <button
              key={s.key}
              onClick={() => toggleSort(s.key)}
              className={`flex items-center gap-1 px-3 py-2 text-xs rounded-xl border transition-colors ${
                sort === s.key
                  ? "bg-foreground/10 border-foreground/20 font-semibold"
                  : "border-foreground/10 hover:bg-foreground/5 text-foreground/60"
              }`}
            >
              {s.label}
              <ArrowUpDown className="w-3 h-3" />
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm p-3">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] overflow-hidden">
        {/* Column headers */}
        <div className="hidden md:flex items-center gap-3 px-4 py-2.5 border-b border-foreground/10 text-xs text-foreground/40 font-medium">
          <div className="w-9 flex-shrink-0" />
          <div className="flex-1">Usuário</div>
          <div className="flex items-center gap-4 flex-shrink-0">
            <span className="flex items-center gap-1 w-16 justify-end"><MessageSquare className="w-3 h-3" /> Msgs</span>
            <span className="flex items-center gap-1 w-16 justify-end"><Mic className="w-3 h-3" /> Voz</span>
            <span className="flex items-center gap-1 w-14 justify-end"><Globe className="w-3 h-3" /> Guild</span>
            <span className="flex items-center gap-1 w-28 justify-end"><Clock className="w-3 h-3" /> Último visto</span>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-foreground/40 text-sm">
            Carregando...
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-foreground/40 gap-2">
            <Users className="w-8 h-8 opacity-30" />
            <p className="text-sm">{search ? "Nenhum usuário encontrado" : "Nenhum usuário monitorado ainda"}</p>
          </div>
        ) : (
          users.map((u) => (
            <UserRow key={u._id} user={u} onClick={() => setSelectedUserId(u._id)} />
          ))
        )}
      </div>

      {/* Pagination */}
      {!loading && total > 0 && (
        <div className="flex items-center justify-between text-xs text-foreground/50">
          <span>{total.toLocaleString()} usuário{total !== 1 ? "s" : ""}</span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="p-1.5 hover:bg-foreground/10 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span>
              Página <strong>{page}</strong> de <strong>{pages}</strong>
            </span>
            <button
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 hover:bg-foreground/10 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* User detail modal */}
      {selectedUserId && (
        <UserDetailModal userId={selectedUserId} onClose={() => setSelectedUserId(null)} />
      )}
    </div>
  );
}