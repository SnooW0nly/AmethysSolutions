"use client";

import { useState, useEffect } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Chip, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faServer, faCheckCircle, faExternalLinkAlt, faUsers } from "@fortawesome/free-solid-svg-icons";
import { CopyIconButton } from "../../CopyIconButton";
import Link from "next/link";

interface BotServerSectionProps {
  appId: string;
  botId: string | null;
  currentServer: string | null;
  tokenConfigured: boolean;
  onUpdate: () => void;
}

export function BotServerSection({ appId, botId, currentServer, tokenConfigured, onUpdate }: BotServerSectionProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newServer, setNewServer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [guildInfo, setGuildInfo] = useState<any>(null);
  const [loadingGuild, setLoadingGuild] = useState(false);

  // Busca URL de convite
  useEffect(() => {
    if (botId && tokenConfigured) {
      fetch(`/api/apps/${appId}/bot/invite`)
        .then(res => res.json())
        .then(data => setInviteUrl(data.inviteUrl))
        .catch(() => {});
    }
  }, [botId, tokenConfigured, appId]);

  // Busca info do servidor
  useEffect(() => {
    if (currentServer && tokenConfigured) {
      setLoadingGuild(true);
      fetch(`/api/apps/${appId}/discord/guild/${currentServer}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => setGuildInfo(data))
        .catch(() => setGuildInfo(null))
        .finally(() => setLoadingGuild(false));
    }
  }, [currentServer, tokenConfigured, appId]);

  // Valida Discord Server ID
  const validateServerId = (id: string): boolean => {
    return /^\d{17,19}$/.test(id);
  };

  const handleUpdate = async () => {
    try {
      setError("");

      if (!newServer.trim()) {
        setError("Server ID não pode estar vazio");
        return;
      }

      if (!validateServerId(newServer)) {
        setError("Server ID inválido. Deve ter 17-19 dígitos.");
        return;
      }

      if (newServer === currentServer) {
        setError("Este já é o servidor atual");
        return;
      }

      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/bot`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ server: newServer }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar servidor");
      }

      addToast({
        title: "Servidor atualizado!",
        description: "Bot reiniciando...",
        color: "success",
      });

      setIsModalOpen(false);
      setNewServer("");
      
      // Reinicia o bot automaticamente
      try {
        const restartRes = await fetch(`/api/apps/${appId}/restart`, {
          method: "POST",
        });
        
        if (restartRes.ok) {
          addToast({
            title: "Bot reiniciando",
            description: "Aguarde alguns segundos...",
            color: "success",
          });
        }
      } catch (err) {
        console.error("Erro ao reiniciar:", err);
      }
      
      onUpdate();
    } catch (err: any) {
      setError(err.message || "Erro ao atualizar servidor");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex flex-col">
        <p className="font-semibold flex items-center gap-2">Servidor Principal</p>
        <p className="text-xs text-foreground/60">
          O servidor principal é onde o bot ficará ativo no Discord e poderá usar comandos.
        </p>
        <hr className="border-foreground/5 mt-2" />
      </div>

      {!tokenConfigured ? (
        <div className="rounded-md bg-warning/10 border border-warning/20 p-4 flex flex-row items-center justify-between">
          <div>
            <p className="font-semibold text-warning text-sm mb-1">Token não configurado</p>
            <p className="text-xs text-foreground/70">Configure o token do bot primeiro antes de configurar o servidor</p>
          </div>
          <Link href={`/dashboard/app/${appId}/restricted`} className="bg-warning/10 border border-warning/20 text-warning px-3 py-2 text-xs font-medium rounded-lg flex flex-row items-center gap-1 hover:bg-warning/20 hover:border-warning/30 transition-all duration-200">Configurar <FontAwesomeIcon className="text-[10px]" icon={faExternalLinkAlt} /></Link>
        </div>
      ) : (
        <>

          <div className="flex flex-col gap-3">
            {/* Info do servidor */}
            {guildInfo ? (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                {guildInfo.icon ? (
                  <Avatar src={guildInfo.icon} name={guildInfo.name} size="sm" showFallback />
                ) : (
                  <div className="w-10 h-10 rounded-md bg-primary/20 flex items-center justify-center">
                    <FontAwesomeIcon icon={faServer} className="text-primary" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{guildInfo.name}</p>
                  <p className="text-xs text-foreground/50 flex items-center gap-1">
                    <FontAwesomeIcon icon={faUsers} className="text-[10px]" />
                    {guildInfo.member_count?.toLocaleString()} membros 
                    • {guildInfo.id} <CopyIconButton value={guildInfo.id || ""} className="text-[10px] text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
                  </p>
                </div>

              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="rounded-md bg-primary/10 border border-primary/20 p-3 text-xs">
                  <p className="font-semibold text-primary mb-1">Passo 2: Configure o Servidor</p>
                  <p className="text-foreground/70">
                    Configure o ID do servidor principal. Sem isso, você não poderá reiniciar a aplicação.
                  </p>
                </div>
              </div>
            )}
              <div className="flex flex-row gap-2">
                <Button
                  variant={inviteUrl ? "flat" : "solid"}
                  color={inviteUrl ? "primary" : "primary"}
                  className="font-normal rounded-lg border border-primary/20 bg-primary/10 text-primary"
                  onPress={() => setIsModalOpen(true)}
                >
                  Configurar Servidor
                </Button>

                {botId && (
                  <Button
                    as="a"
                    href={`https://discord.com/oauth2/authorize?client_id=${botId}&permissions=8&scope=bot%20applications.commands`}
                    target="_blank"
                    rel="noopener noreferrer"
                    color="secondary"
                    variant="flat"
                    className="font-normal rounded-lg border border-foreground/10 bg-foreground/4 text-foreground/70"
                    endContent={<FontAwesomeIcon className="text-[12px]" icon={faExternalLinkAlt} />}
                  >
                    Convite do Bot
                  </Button>
                )}
              </div>
          </div>
        </>
      )}

      {/* Modal de alteração */}
      <Modal isOpen={isModalOpen} onOpenChange={setIsModalOpen}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Configurar Servidor Principal</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-3">
                  {error && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {error}
                    </div>
                  )}

                  {/* Preview do servidor atual (se disponível) */}
                  {loadingGuild ? (
                    <div className="rounded-md bg-foreground/5 border border-foreground/10 p-3 text-xs">
                      Carregando informações do servidor...
                    </div>
                  ) : guildInfo ? (
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                      {guildInfo.icon ? (
                        <Avatar src={guildInfo.icon} name={guildInfo.name} size="sm" showFallback />
                      ) : (
                        <div className="w-10 h-10 rounded-md bg-primary/20 flex items-center justify-center">
                          <FontAwesomeIcon icon={faServer} className="text-primary" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{guildInfo.name}</p>
                        <p className="text-xs text-foreground/50 flex items-center gap-1">
                          <FontAwesomeIcon icon={faUsers} className="text-[10px]" />
                          {guildInfo.member_count?.toLocaleString()} membros 
                          • {guildInfo.id} <CopyIconButton value={guildInfo.id || ""} className="text-[10px] text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
                        </p>
                      </div>
                    </div>
                  ) : currentServer ? (
                    <div className="rounded-md bg-foreground/5 border border-foreground/10 p-3 text-xs">
                      <p className="font-semibold mb-1">Servidor atual:</p>
                      <p className="text-foreground/70 font-mono">{currentServer}</p>
                    </div>
                  ) : null}

                  <Input
                    label="Novo Server ID"
                    placeholder="1410763577224200194"
                    value={newServer}
                    onChange={(e) => {
                      setNewServer(e.target.value);
                      setError("");
                    }}
                    description="Cole o ID do servidor Discord"
                  />

                  <div className="rounded-md bg-foreground/5 border border-foreground/10 p-3 text-xs">
                    <p className="font-semibold mb-1">Como obter Server ID:</p>
                    <ol className="text-foreground/70 list-decimal list-inside space-y-1">
                      <li>Ative o Modo Desenvolvedor no Discord</li>
                      <li>Clique com botão direito no servidor</li>
                      <li>Selecione "Copiar ID do Servidor"</li>
                    </ol>
                  </div>

                  <p className="text-foreground/50 text-xs">
                    O bot precisará ser reiniciado para aplicar esta mudança.
                  </p>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button color="primary" onPress={handleUpdate} isLoading={loading}>
                  Salvar
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
