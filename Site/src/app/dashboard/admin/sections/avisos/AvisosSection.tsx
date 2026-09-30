"use client";

/**
 * AvisosSection — Configurador de Avisos Globais
 *
 * Permite configurar e enviar mensagens Discord (DM) para todos os owners de bots.
 * Suporta: content, embeds (com fields, thumbnail, image, author, footer), components (botões).
 */

import { useState, useEffect, useCallback } from "react";
import { Button, Chip, Spinner, Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBullhorn, faPlus, faTrash, faSave, faPaperPlane,
  faEye, faCode, faChevronDown, faChevronUp, faCopy,
  faExclamationTriangle, faCheckCircle, faTimesCircle,
  faPen, faFilter, faUsers, faXmark, faGripVertical,
  faImage, faLink, faAlignLeft, faHeading, faListUl,
  faSquare, faCircle,
} from "@fortawesome/free-solid-svg-icons";

// ─── Types ────────────────────────────────────────────────────────────────────

type EmbedField = { name: string; value: string; inline: boolean };
type EmbedFooter = { text: string; icon_url?: string };
type EmbedAuthor = { name: string; url?: string; icon_url?: string };
type EmbedImage = { url: string };
type EmbedThumbnail = { url: string };

type Embed = {
  title?: string;
  description?: string;
  color?: number;
  url?: string;
  fields?: EmbedField[];
  footer?: EmbedFooter;
  author?: EmbedAuthor;
  image?: EmbedImage;
  thumbnail?: EmbedThumbnail;
  timestamp?: string;
};

type ButtonComponent = {
  type: 2;
  style: 1 | 2 | 3 | 4 | 5;
  label: string;
  url?: string;
  custom_id?: string;
  emoji?: { name: string };
  disabled?: boolean;
};

type ActionRow = {
  type: 1;
  components: ButtonComponent[];
};

type MessagePayload = {
  content: string;
  embeds: Embed[];
  components: ActionRow[];
  flags: number | null;
};

type SavedConfig = {
  _id: string;
  name: string;
  content: string;
  embeds: Embed[];
  components: ActionRow[];
  flags: number | null;
  updatedAt: string;
  lastSentAt?: string;
  lastSentStats?: any;
};

// ─── Constants ────────────────────────────────────────────────────────────────

const BUTTON_STYLES = [
  { value: 1, label: "Primário", color: "bg-blue-500" },
  { value: 2, label: "Secundário", color: "bg-gray-500" },
  { value: 3, label: "Sucesso", color: "bg-green-500" },
  { value: 4, label: "Perigo", color: "bg-red-500" },
  { value: 5, label: "Link", color: "bg-gray-600" },
];

const EMPTY_EMBED: Embed = {
  title: "",
  description: "",
  color: 0x5865f2,
  url: "",
  fields: [],
  footer: { text: "" },
  author: { name: "" },
  image: { url: "" },
  thumbnail: { url: "" },
};

const EMPTY_BUTTON: ButtonComponent = {
  type: 2,
  style: 1,
  label: "Botão",
  url: "",
  custom_id: "",
};

const EMPTY_PAYLOAD: MessagePayload = {
  content: "",
  embeds: [],
  components: [],
  flags: null,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function hexToInt(hex: string): number {
  return parseInt(hex.replace("#", ""), 16);
}

function intToHex(n: number): string {
  return "#" + n.toString(16).padStart(6, "0");
}

function fmtDate(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleString("pt-BR");
}

// ─── Discord Preview ──────────────────────────────────────────────────────────

function DiscordPreview({ payload }: { payload: MessagePayload }) {
  const hasContent = !!payload.content;
  const hasEmbeds = payload.embeds?.length > 0;
  const hasButtons = payload.components?.some((r) => r.components?.length > 0);

  return (
    <div className="rounded-xl bg-[#313338] p-4 font-['Whitney',_sans-serif] max-w-[520px] space-y-1 select-none">
      {/* Mensagem de sistema (simulada) */}
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-[#5865f2] flex items-center justify-center shrink-0 mt-0.5">
          <FontAwesomeIcon icon={faRobot} className="text-white w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white font-semibold text-sm">Seu Bot</span>
            <span className="text-[10px] bg-[#5865f2] text-white px-1.5 py-0.5 rounded font-semibold">BOT</span>
            <span className="text-[#949ba4] text-xs">Agora</span>
          </div>

          {/* Content */}
          {hasContent && (
            <p className="text-[#dbdee1] text-sm whitespace-pre-wrap leading-[1.375]">
              {payload.content}
            </p>
          )}

          {/* Embeds */}
          {hasEmbeds && payload.embeds.map((embed, i) => (
            <div
              key={i}
              className="mt-1 rounded-sm overflow-hidden"
              style={{
                borderLeft: `4px solid ${intToHex(embed.color || 0x5865f2)}`,
                background: "#2b2d31",
              }}
            >
              <div className="p-3 pr-4">
                {/* Author */}
                {embed.author?.name && (
                  <div className="flex items-center gap-2 mb-2">
                    {embed.author.icon_url && (
                      <img src={embed.author.icon_url} className="w-4 h-4 rounded-full" alt="" />
                    )}
                    <span className="text-[#dbdee1] text-xs font-semibold">{embed.author.name}</span>
                  </div>
                )}

                {/* Title */}
                {embed.title && (
                  <p className={`font-semibold text-sm mb-1 ${embed.url ? "text-[#00aff4] hover:underline cursor-pointer" : "text-white"}`}>
                    {embed.title}
                  </p>
                )}

                {/* Description */}
                {embed.description && (
                  <p className="text-[#dbdee1] text-xs leading-[1.375] whitespace-pre-wrap mb-2">
                    {embed.description}
                  </p>
                )}

                {/* Fields */}
                {embed.fields && embed.fields.length > 0 && (
                  <div className="grid gap-2 mb-2" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
                    {embed.fields.map((f, fi) => (
                      <div key={fi} style={{ gridColumn: f.inline ? "span 1" : "span 3" }}>
                        <p className="text-[#dbdee1] text-xs font-semibold">{f.name}</p>
                        <p className="text-[#dbdee1] text-xs whitespace-pre-wrap">{f.value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Image */}
                {embed.image?.url && (
                  <img
                    src={embed.image.url}
                    className="w-full rounded mt-2 max-h-48 object-cover"
                    alt="embed image"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                )}

                {/* Footer */}
                {embed.footer?.text && (
                  <div className="flex items-center gap-1.5 mt-2">
                    {embed.footer.icon_url && (
                      <img src={embed.footer.icon_url} className="w-4 h-4 rounded-full" alt="" />
                    )}
                    <span className="text-[#949ba4] text-[10px]">{embed.footer.text}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Buttons */}
          {hasButtons && (
            <div className="mt-1 flex flex-wrap gap-2">
              {payload.components.flatMap((row) =>
                (row.components || []).map((btn, bi) => {
                  const styleMeta = BUTTON_STYLES.find((s) => s.value === btn.style);
                  return (
                    <button
                      key={bi}
                      disabled={btn.disabled}
                      className={`px-4 py-1.5 rounded text-white text-xs font-medium transition-opacity ${styleMeta?.color || "bg-blue-500"} ${btn.disabled ? "opacity-40 cursor-not-allowed" : "opacity-90 hover:opacity-100"}`}
                    >
                      {btn.emoji?.name && <span className="mr-1">{btn.emoji.name}</span>}
                      {btn.label}
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>

      {(!hasContent && !hasEmbeds && !hasButtons) && (
        <p className="text-[#949ba4] text-sm text-center py-4 italic">
          Pré-visualização vazia — configure a mensagem ao lado
        </p>
      )}
    </div>
  );
}

// import missing icon
import { faRobot } from "@fortawesome/free-solid-svg-icons";

// ─── Embed Editor ─────────────────────────────────────────────────────────────

function EmbedEditor({ embed, onChange, onRemove }: { embed: Embed; onChange: (e: Embed) => void; onRemove: () => void }) {
  const [open, setOpen] = useState(true);

  const set = (key: keyof Embed, val: any) => onChange({ ...embed, [key]: val });

  return (
    <div className="rounded-xl border border-foreground/10 bg-foreground/[0.015] overflow-hidden">
      {/* Header do embed */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-foreground/5 transition-colors"
        style={{ borderLeft: `3px solid ${intToHex(embed.color || 0x5865f2)}` }}
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <FontAwesomeIcon icon={open ? faChevronUp : faChevronDown} className="w-3 h-3 text-foreground/40" />
          <span className="text-sm font-semibold text-foreground/80">
            {embed.title || "Embed sem título"}
          </span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="p-1.5 rounded-lg hover:bg-danger/10 text-foreground/30 hover:text-danger-500 transition-all"
        >
          <FontAwesomeIcon icon={faTrash} className="w-3 h-3" />
        </button>
      </div>

      {open && (
        <div className="p-4 space-y-4">
          {/* Cor */}
          <div className="flex items-center gap-3">
            <label className="text-xs text-foreground/50 font-medium w-20 shrink-0">Cor</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={intToHex(embed.color || 0x5865f2)}
                onChange={(e) => set("color", hexToInt(e.target.value))}
                className="w-10 h-8 rounded cursor-pointer border border-foreground/10 bg-transparent"
              />
              <span className="text-xs font-mono text-foreground/40">{intToHex(embed.color || 0x5865f2)}</span>
            </div>
          </div>

          {/* Author */}
          <div className="grid grid-cols-2 gap-3">
            <FieldInput icon={faHeading} label="Author name" value={embed.author?.name || ""} onChange={(v) => set("author", { ...embed.author, name: v })} />
            <FieldInput icon={faLink} label="Author icon URL" value={embed.author?.icon_url || ""} onChange={(v) => set("author", { ...embed.author, icon_url: v })} />
          </div>

          {/* Title + URL */}
          <div className="grid grid-cols-2 gap-3">
            <FieldInput icon={faHeading} label="Título" value={embed.title || ""} onChange={(v) => set("title", v)} />
            <FieldInput icon={faLink} label="URL do título" value={embed.url || ""} onChange={(v) => set("url", v)} />
          </div>

          {/* Description */}
          <div>
            <label className="flex items-center gap-2 text-xs text-foreground/50 font-medium mb-1.5">
              <FontAwesomeIcon icon={faAlignLeft} className="w-3 h-3" />
              Descrição
            </label>
            <textarea
              value={embed.description || ""}
              onChange={(e) => set("description", e.target.value)}
              rows={4}
              className="w-full bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-primary/40 transition-colors resize-none text-foreground/90 placeholder:text-foreground/25 font-mono"
              placeholder="Descrição do embed... (suporta markdown)"
            />
          </div>

          {/* Thumbnail + Image */}
          <div className="grid grid-cols-2 gap-3">
            <FieldInput icon={faImage} label="Thumbnail URL" value={embed.thumbnail?.url || ""} onChange={(v) => set("thumbnail", { url: v })} />
            <FieldInput icon={faImage} label="Image URL" value={embed.image?.url || ""} onChange={(v) => set("image", { url: v })} />
          </div>

          {/* Fields */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="flex items-center gap-2 text-xs text-foreground/50 font-medium">
                <FontAwesomeIcon icon={faListUl} className="w-3 h-3" />
                Fields ({embed.fields?.length || 0}/25)
              </label>
              <button
                onClick={() => set("fields", [...(embed.fields || []), { name: "Campo", value: "Valor", inline: false }])}
                className="text-xs px-2 py-1 rounded-lg bg-primary/10 text-primary-400 hover:bg-primary/20 transition-all flex items-center gap-1"
              >
                <FontAwesomeIcon icon={faPlus} className="w-2.5 h-2.5" />
                Field
              </button>
            </div>

            <div className="space-y-2">
              {(embed.fields || []).map((field, fi) => (
                <div key={fi} className="flex items-start gap-2 p-2.5 rounded-lg bg-foreground/5 border border-foreground/10">
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <input
                      value={field.name}
                      onChange={(e) => {
                        const f = [...(embed.fields || [])];
                        f[fi] = { ...f[fi], name: e.target.value };
                        set("fields", f);
                      }}
                      className="bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90"
                      placeholder="Nome"
                    />
                    <input
                      value={field.value}
                      onChange={(e) => {
                        const f = [...(embed.fields || [])];
                        f[fi] = { ...f[fi], value: e.target.value };
                        set("fields", f);
                      }}
                      className="bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90"
                      placeholder="Valor"
                    />
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <label className="flex items-center gap-1 text-xs text-foreground/40 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={field.inline}
                        onChange={(e) => {
                          const f = [...(embed.fields || [])];
                          f[fi] = { ...f[fi], inline: e.target.checked };
                          set("fields", f);
                        }}
                        className="rounded"
                      />
                      Inline
                    </label>
                    <button
                      onClick={() => {
                        const f = [...(embed.fields || [])];
                        f.splice(fi, 1);
                        set("fields", f);
                      }}
                      className="text-foreground/30 hover:text-danger-500 transition-colors"
                    >
                      <FontAwesomeIcon icon={faXmark} className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="grid grid-cols-2 gap-3">
            <FieldInput icon={faAlignLeft} label="Footer text" value={embed.footer?.text || ""} onChange={(v) => set("footer", { ...embed.footer, text: v })} />
            <FieldInput icon={faImage} label="Footer icon URL" value={embed.footer?.icon_url || ""} onChange={(v) => set("footer", { ...embed.footer, icon_url: v })} />
          </div>

          {/* Timestamp */}
          <div className="flex items-center gap-3">
            <label className="text-xs text-foreground/50 font-medium w-20 shrink-0">Timestamp</label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!embed.timestamp}
                onChange={(e) => set("timestamp", e.target.checked ? new Date().toISOString() : undefined)}
                className="rounded"
              />
              <span className="text-xs text-foreground/60">Incluir hora atual</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Button Row Editor ────────────────────────────────────────────────────────

function ButtonRowEditor({ row, onChange, onRemove }: { row: ActionRow; onChange: (r: ActionRow) => void; onRemove: () => void }) {
  const addBtn = () =>
    onChange({ ...row, components: [...row.components, { ...EMPTY_BUTTON, custom_id: `btn_${Date.now()}` }] });

  const removeBtn = (i: number) => {
    const comps = [...row.components];
    comps.splice(i, 1);
    onChange({ ...row, components: comps });
  };

  const setBtn = (i: number, b: ButtonComponent) => {
    const comps = [...row.components];
    comps[i] = b;
    onChange({ ...row, components: comps });
  };

  return (
    <div className="rounded-xl border border-foreground/10 bg-foreground/[0.015] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground/60 flex items-center gap-2">
          <FontAwesomeIcon icon={faSquare} className="w-3 h-3" />
          Linha de Botões ({row.components.length}/5)
        </span>
        <div className="flex items-center gap-2">
          {row.components.length < 5 && (
            <button
              onClick={addBtn}
              className="text-xs px-2 py-1 rounded-lg bg-primary/10 text-primary-400 hover:bg-primary/20 transition-all flex items-center gap-1"
            >
              <FontAwesomeIcon icon={faPlus} className="w-2.5 h-2.5" />
              Botão
            </button>
          )}
          <button
            onClick={onRemove}
            className="p-1.5 rounded-lg hover:bg-danger/10 text-foreground/30 hover:text-danger-500 transition-all"
          >
            <FontAwesomeIcon icon={faTrash} className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {row.components.map((btn, i) => {
          const styleMeta = BUTTON_STYLES.find((s) => s.value === btn.style);
          return (
            <div key={i} className="flex items-center gap-2 p-2.5 rounded-lg bg-foreground/5 border border-foreground/10">
              {/* Style picker */}
              <select
                value={btn.style}
                onChange={(e) => setBtn(i, { ...btn, style: Number(e.target.value) as any })}
                className="bg-foreground/10 border border-foreground/15 rounded-lg px-2 py-1.5 text-xs outline-none text-foreground/80"
              >
                {BUTTON_STYLES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>

              {/* Emoji */}
              <input
                value={btn.emoji?.name || ""}
                onChange={(e) => setBtn(i, { ...btn, emoji: e.target.value ? { name: e.target.value } : undefined })}
                className="w-14 bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90 text-center"
                placeholder="🎉"
              />

              {/* Label */}
              <input
                value={btn.label}
                onChange={(e) => setBtn(i, { ...btn, label: e.target.value })}
                className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90"
                placeholder="Label do botão"
              />

              {/* URL (style 5) or custom_id */}
              {btn.style === 5 ? (
                <input
                  value={btn.url || ""}
                  onChange={(e) => setBtn(i, { ...btn, url: e.target.value })}
                  className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90"
                  placeholder="https://..."
                />
              ) : (
                <input
                  value={btn.custom_id || ""}
                  onChange={(e) => setBtn(i, { ...btn, custom_id: e.target.value })}
                  className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg px-2 py-1.5 text-xs outline-none focus:border-primary/40 text-foreground/90 font-mono"
                  placeholder="custom_id"
                />
              )}

              {/* Disabled toggle */}
              <label className="flex items-center gap-1 text-xs text-foreground/40 cursor-pointer whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={!!btn.disabled}
                  onChange={(e) => setBtn(i, { ...btn, disabled: e.target.checked })}
                />
                Off
              </label>

              <button
                onClick={() => removeBtn(i)}
                className="text-foreground/30 hover:text-danger-500 transition-colors p-1"
              >
                <FontAwesomeIcon icon={faXmark} className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Field Input helper ───────────────────────────────────────────────────────

function FieldInput({ icon, label, value, onChange, mono = false }: {
  icon: any; label: string; value: string; onChange: (v: string) => void; mono?: boolean;
}) {
  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground/50 font-medium mb-1.5">
        <FontAwesomeIcon icon={icon} className="w-3 h-3" />
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full bg-foreground/5 border border-foreground/10 rounded-lg px-3 py-2 text-xs outline-none focus:border-primary/40 transition-colors text-foreground/90 placeholder:text-foreground/25 ${mono ? "font-mono" : ""}`}
        placeholder={label}
      />
    </div>
  );
}

// ─── Send Results Modal ───────────────────────────────────────────────────────

function SendResultsModal({ isOpen, onClose, results }: { isOpen: boolean; onClose: () => void; results: any }) {
  if (!results) return null;
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalContent>
        <ModalHeader className="flex items-center gap-2">
          <FontAwesomeIcon icon={faBullhorn} className="text-primary-400" />
          Resultado do Envio
        </ModalHeader>
        <ModalBody className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Total apps", value: results.total, color: "text-foreground" },
              { label: "Enviados", value: results.sent, color: "text-success-500" },
              { label: "Falhas", value: results.failed, color: "text-danger-500" },
              { label: "Pulados", value: results.skipped, color: "text-warning-500" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-foreground/10 bg-foreground/5 p-3 text-center">
                <p className={`text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</p>
                <p className="text-xs text-foreground/40 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Errors */}
          {results.errors?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-foreground/50 mb-2">
                Erros ({results.errors.length})
              </p>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {results.errors.slice(0, 20).map((err: any, i: number) => (
                  <div key={i} className="text-xs p-2 rounded-lg bg-danger/5 border border-danger/10 font-mono text-foreground/60">
                    <span className="text-danger-400">{err.appName}</span>
                    {err.owner && <span className="text-foreground/40"> ({err.owner})</span>}
                    : {err.error}
                  </div>
                ))}
                {results.errors.length > 20 && (
                  <p className="text-xs text-foreground/40 text-center">... e mais {results.errors.length - 20} erros</p>
                )}
              </div>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <Button color="primary" onPress={onClose}>Fechar</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AvisosSection() {
  const [payload, setPayload] = useState<MessagePayload>(EMPTY_PAYLOAD);
  const [configs, setConfigs] = useState<SavedConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [configName, setConfigName] = useState("Novo Aviso");
  const [activeTab, setActiveTab] = useState<"editor" | "preview" | "json">("editor");
  const [targetFilter, setTargetFilter] = useState<"all" | "active" | "expired">("all");
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sendResults, setSendResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [confirmSend, setConfirmSend] = useState(false);

  // ── Load configs ────────────────────────────────────────────────────────────
  const loadConfigs = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/avisos/configs");
      const data = await res.json();
      if (data.success) setConfigs(data.configs || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  // ── Load a config into the editor ──────────────────────────────────────────
  const loadConfig = (cfg: SavedConfig) => {
    setSelectedConfig(cfg._id);
    setConfigName(cfg.name);
    setPayload({
      content: cfg.content || "",
      embeds: cfg.embeds || [],
      components: cfg.components || [],
      flags: cfg.flags || null,
    });
  };

  const newConfig = () => {
    setSelectedConfig(null);
    setConfigName("Novo Aviso");
    setPayload(EMPTY_PAYLOAD);
  };

  // ── Save config ─────────────────────────────────────────────────────────────
  const saveConfig = async () => {
    setSaving(true);
    try {
      const body = { name: configName, ...payload };
      const url = selectedConfig
        ? `/api/admin/avisos/configs/${selectedConfig}`
        : "/api/admin/avisos/configs";
      const method = selectedConfig ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        if (!selectedConfig) setSelectedConfig(data.config._id);
        await loadConfigs();
      }
    } catch {}
    setSaving(false);
  };

  const deleteConfig = async (id: string) => {
    if (!confirm("Deletar esta configuração?")) return;
    await fetch(`/api/admin/avisos/configs/${id}`, { method: "DELETE" });
    if (selectedConfig === id) newConfig();
    await loadConfigs();
  };

  // ── Send ────────────────────────────────────────────────────────────────────
  const sendAvisos = async () => {
    setSending(true);
    setConfirmSend(false);
    try {
      const res = await fetch("/api/admin/avisos/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          configId: selectedConfig,
          payload,
          targetFilter,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setSendResults(data.results);
        onOpen();
        await loadConfigs();
      }
    } catch {}
    setSending(false);
  };

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const setContent = (v: string) => setPayload((p) => ({ ...p, content: v }));

  const addEmbed = () =>
    setPayload((p) => ({ ...p, embeds: [...p.embeds, { ...EMPTY_EMBED }] }));

  const setEmbed = (i: number, e: Embed) =>
    setPayload((p) => { const embeds = [...p.embeds]; embeds[i] = e; return { ...p, embeds }; });

  const removeEmbed = (i: number) =>
    setPayload((p) => { const embeds = [...p.embeds]; embeds.splice(i, 1); return { ...p, embeds }; });

  const addButtonRow = () =>
    setPayload((p) => ({
      ...p,
      components: [...p.components, { type: 1, components: [{ ...EMPTY_BUTTON, custom_id: `btn_${Date.now()}` }] }],
    }));

  const setRow = (i: number, r: ActionRow) =>
    setPayload((p) => { const components = [...p.components]; components[i] = r; return { ...p, components }; });

  const removeRow = (i: number) =>
    setPayload((p) => { const components = [...p.components]; components.splice(i, 1); return { ...p, components }; });

  const isValid = !!(payload.content || payload.embeds.length > 0);

  const currentConfig = configs.find((c) => c._id === selectedConfig);

  return (
    <div className="flex flex-col gap-5">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10">
            <FontAwesomeIcon icon={faBullhorn} className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold">Avisos Globais</h2>
            <p className="text-xs text-foreground/40">
              Envie mensagens Discord (DM) para os donos de todos os bots
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button size="sm" variant="flat" onPress={newConfig} startContent={<FontAwesomeIcon icon={faPlus} />}>
            Novo
          </Button>
          <Button
            size="sm"
            color="primary"
            variant="flat"
            isLoading={saving}
            onPress={saveConfig}
            startContent={!saving && <FontAwesomeIcon icon={faSave} />}
          >
            Salvar
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[260px_1fr] gap-5">
        {/* ── Saved configs list ── */}
        <div className="space-y-3">
          <p className="text-xs font-semibold text-foreground/50 uppercase tracking-widest">
            Configurações salvas
          </p>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="sm" />
            </div>
          ) : configs.length === 0 ? (
            <div className="text-xs text-foreground/30 text-center py-6 border border-dashed border-foreground/10 rounded-xl">
              Nenhuma config salva ainda
            </div>
          ) : (
            <div className="space-y-2">
              {configs.map((cfg) => (
                <div
                  key={cfg._id}
                  onClick={() => loadConfig(cfg)}
                  className={`group relative rounded-xl border cursor-pointer transition-all p-3 ${
                    selectedConfig === cfg._id
                      ? "border-primary/30 bg-primary/5"
                      : "border-foreground/10 bg-foreground/[0.02] hover:border-foreground/20"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold truncate">{cfg.name}</p>
                      <p className="text-xs text-foreground/40 mt-0.5">
                        Atualizado {fmtDate(cfg.updatedAt)}
                      </p>
                      {cfg.lastSentAt && (
                        <p className="text-xs text-success-500 mt-0.5">
                          Enviado {fmtDate(cfg.lastSentAt)}
                          {cfg.lastSentStats && (
                            <span className="text-foreground/40">
                              {" "}· {cfg.lastSentStats.sent} DMs
                            </span>
                          )}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteConfig(cfg._id); }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-danger/10 text-foreground/30 hover:text-danger-500 transition-all"
                    >
                      <FontAwesomeIcon icon={faTrash} className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Editor + Preview ── */}
        <div className="space-y-4">
          {/* Config name */}
          <div className="flex items-center gap-3">
            <FontAwesomeIcon icon={faPen} className="w-3.5 h-3.5 text-foreground/30" />
            <input
              value={configName}
              onChange={(e) => setConfigName(e.target.value)}
              className="flex-1 bg-foreground/5 border border-foreground/10 rounded-xl px-4 py-2.5 text-sm font-semibold outline-none focus:border-primary/40 transition-colors text-foreground/90"
              placeholder="Nome da configuração"
            />
          </div>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-foreground/10 pb-0">
            {[
              { id: "editor", label: "Editor", icon: faPen },
              { id: "preview", label: "Preview", icon: faEye },
              { id: "json", label: "JSON", icon: faCode },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-foreground/5 text-foreground border-b-2 border-primary-400 -mb-px"
                    : "text-foreground/50 hover:text-foreground/80"
                }`}
              >
                <FontAwesomeIcon icon={tab.icon} className="w-3 h-3" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Editor tab ── */}
          {activeTab === "editor" && (
            <div className="space-y-4">
              {/* Content */}
              <div>
                <label className="flex items-center gap-2 text-xs text-foreground/50 font-medium mb-1.5">
                  <FontAwesomeIcon icon={faAlignLeft} className="w-3 h-3" />
                  Content (texto puro acima dos embeds)
                </label>
                <textarea
                  value={payload.content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={3}
                  className="w-full bg-foreground/5 border border-foreground/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-primary/40 transition-colors resize-none text-foreground/90 placeholder:text-foreground/25 font-mono"
                  placeholder="Olá {owner}! 👋 Temos um aviso importante para você..."
                />
                <p className="text-xs text-foreground/30 mt-1">
                  Dica: use menções como &lt;@userId&gt; ou markdown do Discord
                </p>
              </div>

              {/* Embeds */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-foreground/50 flex items-center gap-2">
                    <FontAwesomeIcon icon={faSquare} className="w-3 h-3" />
                    Embeds ({payload.embeds.length}/10)
                  </span>
                  {payload.embeds.length < 10 && (
                    <button
                      onClick={addEmbed}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-primary/10 text-primary-400 hover:bg-primary/20 transition-all flex items-center gap-1.5 font-medium"
                    >
                      <FontAwesomeIcon icon={faPlus} className="w-2.5 h-2.5" />
                      Adicionar Embed
                    </button>
                  )}
                </div>
                <div className="space-y-3">
                  {payload.embeds.map((embed, i) => (
                    <EmbedEditor
                      key={i}
                      embed={embed}
                      onChange={(e) => setEmbed(i, e)}
                      onRemove={() => removeEmbed(i)}
                    />
                  ))}
                </div>
              </div>

              {/* Components (Buttons) */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-foreground/50 flex items-center gap-2">
                    <FontAwesomeIcon icon={faCircle} className="w-3 h-3" />
                    Botões ({payload.components.length}/5 linhas)
                  </span>
                  {payload.components.length < 5 && (
                    <button
                      onClick={addButtonRow}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-foreground/10 text-foreground/60 hover:bg-foreground/15 transition-all flex items-center gap-1.5 font-medium"
                    >
                      <FontAwesomeIcon icon={faPlus} className="w-2.5 h-2.5" />
                      Linha de Botões
                    </button>
                  )}
                </div>
                <div className="space-y-3">
                  {payload.components.map((row, i) => (
                    <ButtonRowEditor
                      key={i}
                      row={row}
                      onChange={(r) => setRow(i, r)}
                      onRemove={() => removeRow(i)}
                    />
                  ))}
                </div>
              </div>

              {/* Flags */}
              <div>
                <label className="flex items-center gap-2 text-xs text-foreground/50 font-medium mb-2">
                  Flags especiais
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: "Ephemeral (64)", value: 64 },
                    { label: "Suppress Embeds (4)", value: 4 },
                  ].map((f) => (
                    <label key={f.value} className="flex items-center gap-2 text-xs cursor-pointer px-3 py-2 rounded-lg border border-foreground/10 hover:border-foreground/20 transition-colors">
                      <input
                        type="checkbox"
                        checked={!!(payload.flags && (payload.flags & f.value))}
                        onChange={(e) => {
                          const current = payload.flags || 0;
                          setPayload((p) => ({
                            ...p,
                            flags: e.target.checked ? (current | f.value) : (current & ~f.value) || null,
                          }));
                        }}
                      />
                      {f.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Preview tab ── */}
          {activeTab === "preview" && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 p-3 rounded-xl bg-foreground/5 border border-foreground/10">
                <FontAwesomeIcon icon={faEye} className="w-3.5 h-3.5 text-foreground/40" />
                <p className="text-xs text-foreground/50">
                  Pré-visualização aproximada — o resultado final pode variar conforme as configurações do Discord do usuário
                </p>
              </div>
              <div className="flex justify-center">
                <DiscordPreview payload={payload} />
              </div>
            </div>
          )}

          {/* ── JSON tab ── */}
          {activeTab === "json" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-foreground/50">JSON do payload Discord</p>
                <button
                  onClick={() => navigator.clipboard.writeText(JSON.stringify(payload, null, 2))}
                  className="text-xs px-2 py-1 rounded-lg bg-foreground/10 text-foreground/50 hover:bg-foreground/15 transition-all flex items-center gap-1"
                >
                  <FontAwesomeIcon icon={faCopy} className="w-3 h-3" />
                  Copiar
                </button>
              </div>
              <pre className="bg-foreground/5 border border-foreground/10 rounded-xl p-4 text-xs font-mono text-foreground/70 overflow-auto max-h-[500px] whitespace-pre-wrap">
                {JSON.stringify(payload, null, 2)}
              </pre>
            </div>
          )}

          {/* ── Send panel ── */}
          <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-4 space-y-4">
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faUsers} className="w-4 h-4 text-foreground/40" />
              <span className="text-sm font-semibold">Enviar para</span>
            </div>

            {/* Filter */}
            <div className="flex gap-2 flex-wrap">
              {[
                { value: "all", label: "Todos os bots" },
                { value: "active", label: "Apenas ativos (não expirados)" },
                { value: "expired", label: "Apenas expirados" },
              ].map((f) => (
                <button
                  key={f.value}
                  onClick={() => setTargetFilter(f.value as any)}
                  className={`text-xs px-3 py-2 rounded-lg border transition-all ${
                    targetFilter === f.value
                      ? "border-primary/30 bg-primary/10 text-primary-400"
                      : "border-foreground/10 text-foreground/50 hover:border-foreground/20"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Warning */}
            <div className="flex items-start gap-2 p-3 rounded-xl bg-warning/5 border border-warning/15">
              <FontAwesomeIcon icon={faExclamationTriangle} className="w-3.5 h-3.5 text-warning-500 mt-0.5 shrink-0" />
              <p className="text-xs text-foreground/60">
                Isso enviará DMs usando o token de cada bot para o dono respectivo.
                A mensagem é enviada apenas uma vez por owner (bots duplicados são agrupados).
                Certifique-se que o conteúdo está correto antes de enviar.
              </p>
            </div>

            {!confirmSend ? (
              <Button
                color="primary"
                className="w-full"
                isDisabled={!isValid || sending}
                onPress={() => setConfirmSend(true)}
                startContent={<FontAwesomeIcon icon={faPaperPlane} />}
              >
                Enviar Aviso
              </Button>
            ) : (
              <div className="space-y-2">
                <div className="p-3 rounded-xl bg-danger/5 border border-danger/20 text-xs text-danger-400 font-medium text-center">
                  ⚠️ Confirme — isso enviará DMs para os owners de todas as aplicações selecionadas
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Button variant="flat" onPress={() => setConfirmSend(false)}>
                    Cancelar
                  </Button>
                  <Button
                    color="danger"
                    isLoading={sending}
                    onPress={sendAvisos}
                    startContent={!sending && <FontAwesomeIcon icon={faPaperPlane} />}
                  >
                    Confirmar Envio
                  </Button>
                </div>
              </div>
            )}

            {currentConfig?.lastSentStats && (
              <div className="flex items-center gap-3 text-xs text-foreground/40 pt-1">
                <FontAwesomeIcon icon={faCheckCircle} className="text-success-500 w-3 h-3" />
                Último envio: {fmtDate(currentConfig.lastSentAt)} —
                {currentConfig.lastSentStats.sent} enviados,
                {" "}{currentConfig.lastSentStats.failed} falhas,
                {" "}{currentConfig.lastSentStats.skipped} pulados
              </div>
            )}
          </div>
        </div>
      </div>

      <SendResultsModal
        isOpen={isOpen}
        onClose={onClose}
        results={sendResults}
      />
    </div>
  );
}