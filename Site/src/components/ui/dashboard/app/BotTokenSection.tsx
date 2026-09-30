"use client";

import { useState, useEffect } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Chip, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faKey, faEye, faEyeSlash, faCopy, faCheckCircle, faRobot } from "@fortawesome/free-solid-svg-icons";
import { CopyIconButton } from "../../CopyIconButton";

interface BotTokenSectionProps {
  appId: string;
  botId: string | null;
  onUpdate: () => void;
}

export function BotTokenSection({ appId, botId, onUpdate }: BotTokenSectionProps) {
  const [loading, setLoading] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [tokenData, setTokenData] = useState<{ masked: string; token: string | null; configured: boolean } | null>(null);
  const [botInfo, setBotInfo] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newToken, setNewToken] = useState("");
  const [tokenError, setTokenError] = useState("");

  // Busca token (mascarado ou revelado)
  const fetchToken = async (reveal = false) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/bot/token?reveal=${reveal}`);
      if (!res.ok) throw new Error("Erro ao buscar token");
      const data = await res.json();
      setTokenData(data);
      setRevealed(reveal);
    } catch (err: any) {
      addToast({ title: "Erro", description: err.message || "Erro ao buscar token", color: "danger" });
    } finally {
      setLoading(false);
    }
  };

  // Busca info do bot
  const fetchBotInfo = async () => {
    if (!botId) {
      console.log('[BotTokenSection] Bot ID não configurado, pulando busca de info');
      return;
    }
    try {
      console.log('[BotTokenSection] Buscando info do bot...');
      const res = await fetch(`/api/apps/${appId}/discord/info`);
      if (!res.ok) {
        console.log('[BotTokenSection] Erro ao buscar info:', res.status);
        return;
      }
      const data = await res.json();
      console.log('[BotTokenSection] Info do bot recebida:', data);
      setBotInfo(data);
    } catch (err) {
      console.error('[BotTokenSection] Erro ao buscar info do bot:', err);
      setBotInfo(null);
    }
  };

  // Copia token
  const copyToken = async () => {
    if (!tokenData?.token && !tokenData?.masked) return;
    const textToCopy = tokenData.token || tokenData.masked || "";
    await navigator.clipboard.writeText(textToCopy);
    addToast({ title: "Copiado!", description: "Token copiado para área de transferência", color: "success" });
  };

  // Valida formato do token Discord
  const validateToken = (token: string): boolean => {
    // Formato: três partes separadas por pontos
    const regex = /^[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{27,}$/;
    return regex.test(token);
  };

  // Atualiza token
  const handleUpdate = async () => {
    try {
      setTokenError("");
      
      if (!newToken.trim()) {
        setTokenError("Token não pode estar vazio");
        return;
      }

      if (!validateToken(newToken)) {
        setTokenError("Formato de token inválido. Use um token válido do Discord.");
        return;
      }

      setLoading(true);
      const res = await fetch(`/api/apps/${appId}/bot`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: newToken }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar token");
      }

      const data = await res.json();

      addToast({ 
        title: "Token configurado", 
        description: data.botInfo ? `${data.botInfo.username}#${data.botInfo.discriminator} - Bot reiniciando...` : "Bot reiniciando...",
        color: "success" 
      });
      
      setIsModalOpen(false);
      setNewToken("");
      
      // Atualiza info do bot
      await fetchToken(false);
      await fetchBotInfo();
      
      // Reinicia o bot automaticamente se servidor estiver configurado
      if (data.needsRestart) {
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
      }
      
      onUpdate();
    } catch (err: any) {
      setTokenError(err.message || "Erro ao atualizar token");
    } finally {
      setLoading(false);
    }
  };

  // Carrega token mascarado ao montar
  useEffect(() => {
    fetchToken(false);
  }, []);

  // Busca info do bot quando botId mudar
  useEffect(() => {
    if (botId) {
      console.log('[BotTokenSection] Bot ID detectado:', botId);
      fetchBotInfo();
    } else {
      console.log('[BotTokenSection] Sem Bot ID');
      setBotInfo(null);
    }
  }, [botId]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col">
        <p className="font-semibold flex items-center gap-2">Token do bot</p>
        <p className="text-xs text-foreground/60">O token do bot é a chave secreta usada para autenticar seu bot com o Discord.</p>
        <hr className="border-foreground/5 mt-2" />
      </div>

      {/* Info do Bot */}
      {botInfo && tokenData?.configured && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
          <Avatar
            src={botInfo.avatar}
            name={botInfo.username}
            size="sm"
            showFallback
            fallback={<FontAwesomeIcon icon={faRobot} />}
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{botInfo.username}</p>
            <div className="flex flex-row items-center gap-1">
              <p className="text-xs text-foreground/50 truncate font-mono">{botInfo.id}</p>
              <CopyIconButton value={botInfo.id} className="text-xs text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
            </div>
          </div>
        </div>
      )}
      
      <div className="flex gap-2 items-center">
        <Input
          type={revealed ? "text" : "password"}
          value={tokenData?.configured ? (revealed ? tokenData.token || "" : tokenData.masked || "") : ""}
          placeholder={tokenData?.configured ? "••••••••••••••••••••••••••••" : "Token não configurado"}
          className="w-full"
          radius="sm"
          variant="bordered"
          readOnly
          isDisabled={true}
        />
        
        {tokenData?.configured && (
          <>
            <Button
              isIconOnly
              variant="flat"
              onPress={() => fetchToken(!revealed)}
              isLoading={loading}
              title={revealed ? "Ocultar" : "Revelar"}
              className="cursor-pointer rounded-lg"
            >
              <FontAwesomeIcon icon={revealed ? faEyeSlash : faEye} />
            </Button>
            
            <Button
              isIconOnly
              variant="flat"
              onPress={copyToken}
              title="Copiar"
              className="cursor-pointer rounded-lg"
            >
              <FontAwesomeIcon icon={faCopy} />
            </Button>
          </>
        )}
        
        <Button
          color="primary"
          variant="flat"
          className="font-medium rounded-lg border border-primary/20 bg-primary/10 text-primary"
          onPress={() => setIsModalOpen(true)}
        >
          {tokenData?.configured ? "Atualizar" : "Configurar"}
        </Button>
      </div>
      
      {!tokenData?.configured && (
        <div className="rounded-md bg-primary/10 border border-primary/20 p-3 text-xs">
          <p className="font-semibold text-primary mb-1">Passo 1: Configure o Token</p>
          <p className="text-foreground/70">
            Configure o token do seu bot aqui. Após isso, você precisará configurar o ID do servidor antes de poder reiniciar a aplicação.
          </p>
        </div>
      )}

      {/* Modal de atualização */}
      <Modal isOpen={isModalOpen} onOpenChange={setIsModalOpen}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Atualizar Token do Bot</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-3">
                  {tokenError && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {tokenError}
                    </div>
                  )}
                  
                  {/* Preview do bot atual (se disponível) */}
                  {botInfo && (
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                      <Avatar
                        src={botInfo.avatar}
                        name={botInfo.username}
                        size="sm"
                        showFallback
                        fallback={<FontAwesomeIcon icon={faRobot} />}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{botInfo.username}</p>
                        <div className="flex flex-row items-center gap-1">
                          <p className="text-xs text-foreground/50 truncate font-mono">{botInfo.id}</p>
                          <CopyIconButton value={botInfo.id} className="text-[10px] text-foreground/50 cursor-pointer hover:text-foreground/80 transition-all duration-100" />
                        </div>
                      </div>
                      {tokenData?.configured && (
                        <Chip size="sm" color="success" variant="flat" startContent={<FontAwesomeIcon icon={faCheckCircle} className="text-success" />}>
                          Configurado
                        </Chip>
                      )}
                    </div>
                  )}
                  
                  <Input
                    label="Novo Token"
                    placeholder="MTQxMDc2NDk1MjE0MjA5MDM2NQ.G-C4rt.AnA..."
                    value={newToken}
                    onChange={(e) => {
                      setNewToken(e.target.value);
                      setTokenError("");
                    }}
                    type="password"
                    description="Cole o token do seu bot Discord aqui"
                  />
                  
                  <p className="text-foreground/50 text-xs">
                    Reinicie o bot após atualizar o token.
                  </p>
                </div>
              </ModalBody>
              <ModalFooter>
                <Button variant="light" onPress={onClose}>
                  Cancelar
                </Button>
                <Button 
                  color="primary" 
                  onPress={handleUpdate}
                  isLoading={loading}
                >
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
