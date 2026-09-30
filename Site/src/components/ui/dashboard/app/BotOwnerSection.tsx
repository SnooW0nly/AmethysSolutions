"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCrown, faExclamationTriangle, faEnvelope, faLock, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { CopyIconButton } from "../../CopyIconButton";

interface BotOwnerSectionProps {
  appId: string;
  currentOwner: string | null;
  onUpdate: () => void;
}

export function BotOwnerSection({ appId, currentOwner, onUpdate }: BotOwnerSectionProps) {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [newOwner, setNewOwner] = useState("");
  const [confirmationCode, setConfirmationCode] = useState("");
  const [transferId, setTransferId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [ownerInfo, setOwnerInfo] = useState<any>(null);
  const [newOwnerInfo, setNewOwnerInfo] = useState<any>(null);
  const [step, setStep] = useState<"input" | "confirm">("input");

  // Busca info do owner
  useEffect(() => {
    if (currentOwner) {
      fetch(`/api/apps/${appId}/discord/user/${currentOwner}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => setOwnerInfo(data))
        .catch(() => setOwnerInfo(null));
    }
  }, [currentOwner]);

  // Valida Discord ID
  const validateDiscordId = (id: string): boolean => {
    return /^\d{17,19}$/.test(id);
  };

  // Busca informações do novo dono quando o ID é digitado
  useEffect(() => {
    if (newOwner && validateDiscordId(newOwner)) {
      fetch(`/api/apps/${appId}/discord/user/${newOwner}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => setNewOwnerInfo(data))
        .catch(() => setNewOwnerInfo(null));
    } else {
      setNewOwnerInfo(null);
    }
  }, [newOwner, appId]);

  // Inicia o processo de transferência
  const handleInitiateTransfer = async () => {
    try {
      setError("");

      if (!newOwner.trim()) {
        setError("Discord ID não pode estar vazio");
        return;
      }

      if (!validateDiscordId(newOwner)) {
        setError("Discord ID inválido. Deve ter 17-19 dígitos.");
        return;
      }

      if (newOwner === currentOwner) {
        setError("Este já é o owner atual");
        return;
      }

      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/transfer-owner/initiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newOwnerDiscordId: newOwner }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Erro ao iniciar transferência");
      }

      setTransferId(data.transferId);
      setStep("confirm");
      setIsConfirmModalOpen(true);
      setIsModalOpen(false);
      
      addToast({
        title: "Código enviado!",
        description: "Verifique seu email para o código de confirmação",
        color: "warning",
      });
    } catch (err: any) {
      setError(err.message || "Erro ao iniciar transferência");
    } finally {
      setLoading(false);
    }
  };

  // Confirma a transferência com o código
  const handleConfirmTransfer = async () => {
    try {
      setConfirmError("");

      if (!confirmationCode.trim() || confirmationCode.length !== 6) {
        setConfirmError("Código deve ter 6 dígitos");
        return;
      }

      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/transfer-owner/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          transferId,
          code: confirmationCode 
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Erro ao confirmar transferência");
      }

      addToast({
        title: "Transferência concluída!",
        description: "A posse foi transferida com sucesso",
        color: "success",
      });

      // Redireciona para o dashboard
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);

      setIsConfirmModalOpen(false);
      resetState();
    } catch (err: any) {
      setConfirmError(err.message || "Erro ao confirmar transferência");
    } finally {
      setLoading(false);
    }
  };

  // Cancela a transferência
  const handleCancelTransfer = async () => {
    if (transferId) {
      try {
        await fetch(`/api/apps/${appId}/transfer-owner/cancel`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transferId }),
        });
      } catch (err) {
        console.error("Erro ao cancelar transferência:", err);
      }
    }
    resetState();
  };

  // Reseta o estado
  const resetState = () => {
    setNewOwner("");
    setConfirmationCode("");
    setTransferId(null);
    setError("");
    setConfirmError("");
    setStep("input");
    setNewOwnerInfo(null);
    setIsModalOpen(false);
    setIsConfirmModalOpen(false);
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col">
        <p className="font-semibold flex items-center gap-2">Proprietário do bot</p>
        <p className="text-xs text-foreground/60">O proprietário do bot é o usuário que possui o bot e pode controlar todas as configurações do bot.</p>
        <hr className="border-foreground/5 mt-2" />
      </div>

      {/* Info do Owner */}
      {ownerInfo ? (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
          <Avatar
            src={ownerInfo.avatar}
            name={ownerInfo.global_name || ownerInfo.username}
            size="sm"
            showFallback
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate flex items-center gap-1">
              {ownerInfo.global_name || ownerInfo.username}
              <span className="text-xs text-foreground/50 truncate">
                @{ownerInfo.username}
              </span>
            </p>
            <div className="flex items-center gap-1">
              <p className="text-xs text-foreground/50 truncate select-all">{currentOwner || "Não configurado"}</p>
              <CopyIconButton value={currentOwner || ""} className="text-xs text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
            </div>
          </div>
          
        </div>
      ) : (
        <div className="flex gap-2 items-center">
          <Input
            value={currentOwner || "Não configurado"}
            className="w-full"
            radius="sm"
            variant="bordered"
            readOnly
            isDisabled={!currentOwner}
          />
        </div>
      )}

      {/* Ações inferiores fora do container principal */}
      <div className="flex flex-row gap-2">
        <Button
          color="primary"
          variant="flat"
          className="font-medium rounded-lg border border-primary/20 bg-primary/10 text-primary"
          onPress={() => setIsModalOpen(true)}
        >
          Alterar Proprietario
        </Button>
        <Button
          as="a"
          href={`https://discord.com/users/${currentOwner ?? ""}`}
          target="_blank"
          rel="noopener noreferrer"
          variant="flat"
          className="font-normal rounded-lg border border-foreground/10 bg-foreground/4 text-foreground/70"
          isDisabled={!currentOwner}
          endContent={<FontAwesomeIcon className="text-[12px]" icon={faExternalLinkAlt} />}
        >
          Usuário no Discord
        </Button>
      </div>

      {/* Modal de transferência - Etapa 1 */}
      <Modal isOpen={isModalOpen} onOpenChange={setIsModalOpen} size="lg">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex items-center gap-2">
                Transferência de Posse
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  {/* Aviso importante */}
                  <div className="rounded-lg bg-danger/10 border border-danger/20 p-4">
                    <div className="flex items-start gap-3">
                      <FontAwesomeIcon icon={faExclamationTriangle} className="text-danger mt-1" />
                      <div>
                        <p className="font-semibold text-danger mb-1">Atenção - Ação Irreversível</p>
                        <p className="text-sm text-foreground/70">
                          Ao transferir a posse, você perderá completamente o acesso ao bot.
                          O novo proprietário terá controle total sobre a aplicação.
                        </p>
                      </div>
                    </div>
                  </div>

                  {error && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-sm p-3">
                      {error}
                    </div>
                  )}

                  {/* Owner atual */}
                  <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-3">
                    <p className="text-xs font-semibold text-foreground/60 mb-2">OWNER ATUAL</p>
                    {ownerInfo ? (
                      <div className="flex items-center gap-3">
                        <Avatar
                          src={ownerInfo.avatar}
                          name={ownerInfo.global_name || ownerInfo.username}
                          size="sm"
                        />
                        <div>
                          <p className="font-medium">{ownerInfo.global_name || ownerInfo.username}</p>
                          <p className="text-xs text-foreground/50">ID: {currentOwner}</p>
                        </div>
                      </div>
                    ) : (
                      <p className="font-mono text-sm">{currentOwner || "Não configurado"}</p>
                    )}
                  </div>

                  {/* Novo owner */}
                  <div>
                    <Input
                      label="Discord ID do Novo Proprietário"
                      placeholder="1303763805213298690"
                      value={newOwner}
                      onChange={(e) => {
                        setNewOwner(e.target.value);
                        setError("");
                      }}
                      description="Digite o Discord ID de quem receberá a posse"
                      variant="bordered"
                    />
                    
                    {newOwnerInfo && (
                      <div className="mt-3 p-3 rounded-lg bg-success/10 border border-success/20">
                        <p className="text-xs font-semibold text-success mb-2">NOVO PROPRIETÁRIO</p>
                        <div className="flex items-center gap-3">
                          <Avatar
                            src={newOwnerInfo.avatar}
                            name={newOwnerInfo.global_name || newOwnerInfo.username}
                            size="sm"
                          />
                          <div>
                            <p className="font-medium">{newOwnerInfo.global_name || newOwnerInfo.username}</p>
                            <p className="text-xs text-foreground/50">@{newOwnerInfo.username}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="text-xs text-foreground/50 space-y-1">
                    <p>• Um código de confirmação será enviado para seu email</p>
                    <p>• O novo proprietário receberá uma notificação via Discord</p>
                    <p>• Você será redirecionado ao dashboard após a transferência</p>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button 
                  color="danger" 
                  onPress={handleInitiateTransfer} 
                  isLoading={loading}
                  isDisabled={!newOwner || !validateDiscordId(newOwner) || newOwner === currentOwner}
                  startContent={<FontAwesomeIcon icon={faEnvelope} />}
                >
                  Enviar Código de Confirmação
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>

      {/* Modal de confirmação - Etapa 2 */}
      <Modal 
        isOpen={isConfirmModalOpen} 
        onOpenChange={(open) => {
          if (!open) handleCancelTransfer();
          setIsConfirmModalOpen(open);
        }}
        size="md"
        isDismissable={false}
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex items-center gap-2">
                <FontAwesomeIcon icon={faEnvelope} className="text-warning" />
                Confirmar Transferência
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  <div className="rounded-lg bg-warning/10 border border-warning/20 p-4">
                    <p className="text-sm font-semibold text-warning mb-1">
                      Código enviado para seu email!
                    </p>
                    <p className="text-xs text-foreground/70">
                      Digite o código de 6 dígitos para confirmar a transferência.
                    </p>
                  </div>

                  {confirmError && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-sm p-3">
                      {confirmError}
                    </div>
                  )}

                  <Input
                    placeholder="000000"
                    value={confirmationCode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setConfirmationCode(value);
                      setConfirmError("");
                    }}
                    maxLength={6}
                    variant="bordered"
                    size="lg"
                    classNames={{
                      input: "text-center text-2xl font-bold tracking-widest",
                    }}
                  />

                  <div className="rounded-lg bg-danger/5 border border-danger/10 p-3">
                    <p className="text-xs text-foreground/70">
                      <strong>Lembrete:</strong> Após confirmar, você perderá imediatamente o acesso ao bot.
                    </p>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button 
                  variant="light" 
                  onPress={handleCancelTransfer}
                >
                  Cancelar
                </Button>
                <Button 
                  color="danger" 
                  onPress={handleConfirmTransfer} 
                  isLoading={loading}
                  isDisabled={confirmationCode.length !== 6}
                >
                  Confirmar Transferência
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
