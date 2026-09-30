"use client";

// src/app/dashboard/admin/sections/bot/BotBioSection.tsx
// Seção para gerenciar a bio global de todos os bots

import { useState, useEffect } from "react";
import { Button, Textarea, Chip } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSave, faRotate, faInfoCircle } from "@fortawesome/free-solid-svg-icons";

export function BotBioSection() {
  const [bio, setBio] = useState("");
  const [originalBio, setOriginalBio] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadBio = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/admin/bot/bio");
      if (res.ok) {
        const data = await res.json();
        setBio(data.bio || "");
        setOriginalBio(data.bio || "");
        setUpdatedAt(data.updatedAt);
      }
    } catch (err) {
      console.error("Erro ao buscar bio:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBio();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const res = await fetch("/api/admin/bot/bio", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bio }),
      });
      const data = await res.json();
      if (res.ok) {
        setOriginalBio(bio);
        setUpdatedAt(data.updatedAt);
        setMessage({ type: "success", text: "Bio atualizada! Os bots vão buscar a nova bio no próximo ciclo (1 minuto)." });
      } else {
        setMessage({ type: "error", text: data.error || "Erro ao salvar" });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Erro de conexão" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = bio !== originalBio;

  return (
    <div className="rounded-xl border border-foreground/10 bg-foreground/[0.02] p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm">Biografia Global dos Bots</h3>
          <p className="text-xs text-foreground/50 mt-0.5">
            Todos os bots vão buscar essa bio da API e aplicar automaticamente a cada 1 minuto
          </p>
        </div>
        {updatedAt && (
          <Chip size="sm" variant="flat" className="text-xs text-foreground/50">
            Atualizado {new Date(updatedAt).toLocaleString("pt-BR")}
          </Chip>
        )}
      </div>

      {/* Info */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-primary/5 border border-primary/15">
        <FontAwesomeIcon icon={faInfoCircle} className="text-primary text-xs mt-0.5 shrink-0" />
        <p className="text-xs text-foreground/70">
          A bio aqui substituirá a bio hardcoded dos bots. Se deixar vazio, os bots usarão o fallback padrão local.
          Os bots autenticam com o <code className="text-xs bg-foreground/10 px-1 rounded">botToken</code> para buscar via{" "}
          <code className="text-xs bg-foreground/10 px-1 rounded">GET /bot/bio</code>.
        </p>
      </div>

      {/* Textarea */}
      {loading ? (
        <div className="h-24 rounded-lg bg-foreground/5 animate-pulse" />
      ) : (
        <Textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          placeholder="Digite a bio que todos os bots vão usar..."
          minRows={3}
          maxRows={8}
          maxLength={400}
          description={`${bio.length}/400 caracteres`}
          classNames={{
            input: "text-sm font-mono",
          }}
        />
      )}

      {/* Feedback */}
      {message && (
        <div
          className={`text-xs p-3 rounded-lg border ${
            message.type === "success"
              ? "bg-success/10 border-success/20 text-success-700"
              : "bg-danger/10 border-danger/20 text-danger-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Ações */}
      <div className="flex items-center gap-2 justify-end">
        <Button
          size="sm"
          variant="light"
          onPress={loadBio}
          isDisabled={loading || saving}
          startContent={<FontAwesomeIcon icon={faRotate} />}
        >
          Recarregar
        </Button>
        <Button
          size="sm"
          color="primary"
          onPress={handleSave}
          isDisabled={!hasChanges || saving || loading}
          isLoading={saving}
          startContent={<FontAwesomeIcon icon={faSave} />}
        >
          Salvar Bio
        </Button>
      </div>
    </div>
  );
}