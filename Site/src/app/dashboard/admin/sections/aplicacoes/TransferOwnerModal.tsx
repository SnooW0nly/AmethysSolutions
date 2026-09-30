"use client";

// src/app/dashboard/admin/sections/aplicacoes/TransferOwnerModal.tsx
// Modal para transferir owner direto no banco (sem verificação de email)

import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Chip,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExchangeAlt, faUser, faExclamationTriangle, faCheckCircle } from "@fortawesome/free-solid-svg-icons";
import { Application } from "@/types/application";

interface TransferOwnerModalProps {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function TransferOwnerModal({
  application,
  isOpen,
  onClose,
  onSuccess,
}: TransferOwnerModalProps) {
  const [newOwnerDiscordId, setNewOwnerDiscordId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const currentOwner =
    application.bot?.owner ||
    application.userId?.discordId ||
    "Não identificado";

  const isValidDiscordId = /^\d{17,19}$/.test(newOwnerDiscordId.trim());

  const handleTransfer = async () => {
    if (!isValidDiscordId) return;

    const confirmed = window.confirm(
      `Tem certeza que deseja transferir a posse de "${application.name}" ` +
        `para o Discord ID ${newOwnerDiscordId}?\n\n` +
        `Esta ação é feita diretamente no banco de dados, sem confirmação por email.`
    );
    if (!confirmed) return;

    try {
      setLoading(true);
      setError(null);

      const res = await fetch(
        `/api/admin/applications/${application._id}/transfer-owner`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ newOwnerDiscordId: newOwnerDiscordId.trim() }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Erro ao transferir posse");
      }

      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Erro ao transferir posse");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (loading) return;
    setNewOwnerDiscordId("");
    setError(null);
    setSuccess(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <ModalContent>
        {() => (
          <>
            <ModalHeader className="flex items-center gap-2">
              <FontAwesomeIcon icon={faExchangeAlt} className="text-warning" />
              <span>Transferir Posse</span>
            </ModalHeader>

            <ModalBody className="space-y-4">
              {/* Info da aplicação */}
              <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                <p className="text-xs text-foreground/50 mb-1">Aplicação</p>
                <p className="font-semibold text-sm">{application.name}</p>
                <p className="text-xs text-foreground/50 mt-1">
                  ID: {application._id}
                </p>
              </div>

              {/* Owner atual */}
              <div className="flex items-center gap-3">
                <div className="flex-1 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                  <p className="text-xs text-foreground/50 mb-1">Owner Atual</p>
                  <div className="flex items-center gap-2">
                    <FontAwesomeIcon icon={faUser} className="text-foreground/40 text-xs" />
                    <p className="text-sm font-mono">{currentOwner}</p>
                  </div>
                </div>
                <FontAwesomeIcon
                  icon={faExchangeAlt}
                  className="text-foreground/30 text-sm"
                />
                <div className="flex-1 p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <p className="text-xs text-foreground/50 mb-1">Novo Owner</p>
                  <p className="text-sm font-mono text-primary">
                    {newOwnerDiscordId || "—"}
                  </p>
                </div>
              </div>

              {/* Aviso */}
              <div className="flex items-start gap-2 p-3 rounded-lg bg-warning/8 border border-warning/20">
                <FontAwesomeIcon
                  icon={faExclamationTriangle}
                  className="text-warning text-xs mt-0.5 shrink-0"
                />
                <p className="text-xs text-foreground/70">
                  Esta ação altera diretamente o banco de dados:{" "}
                  <strong>userId</strong>, <strong>bot.owner</strong> e{" "}
                  <strong>bot.perms</strong> serão atualizados. O BotConfig
                  associado também será sincronizado.
                </p>
              </div>

              {/* Input do novo Discord ID */}
              <Input
                label="Discord ID do Novo Owner"
                placeholder="Ex: 1242662535619153920"
                value={newOwnerDiscordId}
                onChange={(e) => {
                  setNewOwnerDiscordId(e.target.value);
                  setError(null);
                }}
                description="ID numérico do Discord (17-19 dígitos)"
                isInvalid={!!newOwnerDiscordId && !isValidDiscordId}
                errorMessage="Discord ID inválido (deve ter 17 a 19 dígitos)"
                startContent={
                  <FontAwesomeIcon
                    icon={faUser}
                    className="text-foreground/40 text-xs"
                  />
                }
                endContent={
                  isValidDiscordId ? (
                    <FontAwesomeIcon
                      icon={faCheckCircle}
                      className="text-success text-xs"
                    />
                  ) : null
                }
              />

              {/* Erro */}
              {error && (
                <div className="text-xs p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger-600">
                  {error}
                </div>
              )}

              {/* Sucesso */}
              {success && (
                <div className="text-xs p-3 rounded-lg bg-success/10 border border-success/20 text-success-700">
                  ✅ Posse transferida com sucesso!
                </div>
              )}
            </ModalBody>

            <ModalFooter>
              <Button
                variant="light"
                onPress={handleClose}
                isDisabled={loading}
              >
                Cancelar
              </Button>
              <Button
                color="warning"
                onPress={handleTransfer}
                isDisabled={!isValidDiscordId || loading || success}
                isLoading={loading}
                startContent={<FontAwesomeIcon icon={faExchangeAlt} />}
              >
                Transferir Posse
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}