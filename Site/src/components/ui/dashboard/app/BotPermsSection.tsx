"use client";

import { useState, useEffect } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Chip, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faShieldHalved, faUserPlus, faTrash, faCheckCircle, faCrown, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { CopyIconButton } from "@/components/ui/CopyIconButton";
import Link from "next/link";

interface BotPermsSectionProps {
  appId: string;
  currentPerms: string[];
  currentOwner: string | null;
  serverConfigured: boolean;
  tokenConfigured?: boolean;
  onUpdate: () => void;
}

export function BotPermsSection({ appId, currentPerms, currentOwner, serverConfigured, tokenConfigured = false, onUpdate }: BotPermsSectionProps) {
  // Garante que o owner apareça sempre na UI
  const initialPerms = Array.from(new Set([...(currentPerms || []), ...(currentOwner ? [currentOwner] : [])]));
  const [perms, setPerms] = useState<string[]>(initialPerms);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newPerm, setNewPerm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasChanges, setHasChanges] = useState(false);
  const [usersInfo, setUsersInfo] = useState<Record<string, any>>({});

  // Busca info dos usuários
  useEffect(() => {
    if (perms.length > 0 && serverConfigured) {
      fetch(`/api/apps/${appId}/discord/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userIds: perms }),
      })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.users) {
            const usersMap: Record<string, any> = {};
            data.users.forEach((u: any) => {
              usersMap[u.id] = u;
            });
            setUsersInfo(usersMap);
          }
        })
        .catch(() => {});
    }
  }, [perms, serverConfigured]);

  // Valida Discord ID
  const validateDiscordId = (id: string): boolean => {
    return /^\d{17,19}$/.test(id);
  };

  // Adiciona permissão
  const handleAdd = () => {
    setError("");

    if (!newPerm.trim()) {
      setError("Discord ID não pode estar vazio");
      return;
    }

    if (!validateDiscordId(newPerm)) {
      setError("Discord ID inválido. Deve ter 17-19 dígitos.");
      return;
    }

    if (perms.includes(newPerm)) {
      setError("Este usuário já tem permissão");
      return;
    }

    setPerms([...perms, newPerm]);
    setHasChanges(true);
    setNewPerm("");
    setIsAddModalOpen(false);
    addToast({ title: "Adicionado!", description: "Clique em 'Salvar' para aplicar", color: "success" });
  };

  // Remove permissão
  const handleRemove = (id: string) => {
    if (id === currentOwner) {
      addToast({ title: "Erro", description: "Não é possível remover o owner", color: "danger" });
      return;
    }

    setPerms(perms.filter((p) => p !== id));
    setHasChanges(true);
    addToast({ title: "Removido!", description: "Clique em 'Salvar' para aplicar", color: "success" });
  };

  // Salva alterações
  const handleSave = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/bot`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ perms }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar permissões");
      }

      addToast({
        title: "Permissões atualizadas!",
        description: "Bot reiniciando...",
        color: "success",
      });

      setHasChanges(false);
      
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
      addToast({ title: "Erro", description: err.message || "Erro ao salvar", color: "danger" });
    } finally {
      setLoading(false);
    }
  };

  // Cancela alterações
  const handleCancel = () => {
    setPerms(currentPerms || []);
    setHasChanges(false);
    addToast({ title: "Cancelado", description: "Alterações descartadas", color: "default" });
  };

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex flex-col">
        <div className="flex flex-row items-center justify-between gap-5">
          <div className="flex flex-col">
            <p className="font-semibold flex items-center gap-2">Permissões</p>
            <p className="text-xs text-foreground/60 max-w-[200px] xl:max-w-none">
              Defina as pessoas que podem gerenciar as configurações do bot nesta aplicação.
            </p>
          </div>
          {(
            <Button
              color="primary"
              variant="flat"
              startContent={<FontAwesomeIcon icon={faUserPlus} />}
              onPress={() => setIsAddModalOpen(true)}
              className="font-normal rounded-lg border border-primary/20 bg-primary/10 text-primary"
              isDisabled={!serverConfigured}
            >
              Adicionar
            </Button>
          )}
        </div>
        <hr className="border-foreground/5 mt-2" />
      </div>

      {!serverConfigured ? (
        <div className="rounded-md bg-warning/10 border border-warning/20 p-4 flex flex-row items-center justify-between">
          <div>
            <p className="font-semibold text-warning text-sm mb-1">Servidor não configurado</p>
            <p className="text-xs text-foreground/70">Configure o servidor principal primeiro antes de gerenciar permissões</p>
          </div>
          <Link href={`/dashboard/app/${appId}/overview`} className="bg-warning/10 border border-warning/20 text-warning px-3 py-2 text-xs font-medium rounded-lg flex flex-row items-center gap-1 hover:bg-warning/20 hover:border-warning/30 transition-all duration-200">Configurar <FontAwesomeIcon className="text-[10px]" icon={faExternalLinkAlt} /></Link>
        </div>
      ) : (
        <>

      {/* Lista de permissões */}
      <div className="flex flex-col gap-2 overflow-y-auto max-h-[300px]">
        {perms.length === 0 ? (
          <div className="rounded-md bg-foreground/5 border border-foreground/10 p-4 text-center text-sm text-foreground/60">
            Nenhuma permissão configurada
          </div>
        ) : (
          perms.map((id) => {
            const userInfo = usersInfo[id];
            const isOwner = id === currentOwner;
            
            return (
              <div
                key={id}
                className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10"
              >
                <Avatar
                  src={userInfo?.avatar}
                  name={userInfo?.global_name || userInfo?.username || id}
                  size="sm"
                  showFallback
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">
                      {userInfo?.global_name || userInfo?.username || "Usuário"}
                    </p>
                    <p className="text-xs text-foreground/50 truncate">
                      {userInfo?.username ? `@${userInfo.username}` : id}
                    </p>
                    {isOwner && (
                      <FontAwesomeIcon icon={faCrown} className="text-warning text-xs" title="Owner" />
                    )}
                  </div>
                  <div className="flex flex-row items-center gap-1">
                    <p className="text-[11px] text-foreground/50 truncate">{id}</p>
                    <CopyIconButton value={id} className="text-[11px] text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
                  </div>
                </div>

                {!isOwner && (
                  <Button
                    isIconOnly
                    size="sm"
                    color="danger"
                    variant="light"
                    onPress={() => handleRemove(id)}
                  >
                    <FontAwesomeIcon icon={faTrash} />
                  </Button>
                )}
              </div>
            );
          })
        )}
      </div>

          {/* Botões de ação */}
          {hasChanges && (
            <div className="flex gap-2 mt-auto">
              <Button variant="light" onPress={handleCancel} className="flex-1">
                Cancelar
              </Button>
              <Button color="primary" onPress={handleSave} isLoading={loading} className="flex-1">
                Salvar Alterações
              </Button>
            </div>
          )}
        </>
      )}

      {/* Modal de adicionar */}
      <Modal isOpen={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Adicionar Permissão</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-3">
                  {error && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {error}
                    </div>
                  )}

                  <Input
                    label="Discord ID"
                    placeholder="1303763805213298690"
                    value={newPerm}
                    onChange={(e) => {
                      setNewPerm(e.target.value);
                      setError("");
                    }}
                    description="Cole o Discord ID do usuário"
                    autoFocus
                  />

                  <div className="rounded-md bg-foreground/5 border border-foreground/10 p-3 text-xs">
                    <p className="font-semibold mb-1">Como obter Discord ID:</p>
                    <ol className="text-foreground/70 list-decimal list-inside space-y-1">
                      <li>Ative o Modo Desenvolvedor no Discord</li>
                      <li>Clique com botão direito no usuário</li>
                      <li>Selecione "Copiar ID"</li>
                    </ol>
                  </div>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button color="primary" onPress={handleAdd}>
                  Adicionar
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
