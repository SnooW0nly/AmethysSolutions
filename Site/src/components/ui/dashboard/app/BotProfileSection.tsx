"use client";

import { useState, useEffect, useRef } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faEdit, faImage, faPanorama } from "@fortawesome/free-solid-svg-icons";

interface BotProfileSectionProps {
  appId: string;
  botId: string | null;
  tokenConfigured: boolean;
  onUpdate: () => void;
}

interface BotProfile {
  username: string;
  discriminator: string;
  avatar: string | null;
  banner: string | null;
}

export function BotProfileSection({ appId, botId, tokenConfigured, onUpdate }: BotProfileSectionProps) {
  const [profile, setProfile] = useState<BotProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  // Busca perfil do bot
  useEffect(() => {
    if (botId && tokenConfigured) {
      setLoading(true);
      fetch(`/api/apps/${appId}/bot/profile`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data) {
            setProfile(data);
            setNewUsername(data.username);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [botId, tokenConfigured, appId]);

  // Converte arquivo para base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        // Remove o prefixo "data:image/...;base64,"
        const base64Data = base64.split(',')[1];
        resolve(`data:image/${file.type.split('/')[1]};base64,${base64Data}`);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  // Handle avatar upload
  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 8 * 1024 * 1024) {
        setError("Avatar deve ter no máximo 8MB");
        return;
      }
      setAvatarFile(file);
      const url = URL.createObjectURL(file);
      setAvatarPreview(url);
      setError("");
    }
  };

  // Handle banner upload
  const handleBannerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 8 * 1024 * 1024) {
        setError("Banner deve ter no máximo 8MB");
        return;
      }
      setBannerFile(file);
      const url = URL.createObjectURL(file);
      setBannerPreview(url);
      setError("");
    }
  };

  // Atualiza perfil
  const handleUpdate = async () => {
    try {
      setError("");
      setLoading(true);

      const updates: any = {};

      if (newUsername && newUsername !== profile?.username) {
        updates.username = newUsername;
      }

      if (avatarFile) {
        updates.avatar = await fileToBase64(avatarFile);
      }

      if (bannerFile) {
        updates.banner = await fileToBase64(bannerFile);
      }

      if (Object.keys(updates).length === 0) {
        setError("Nenhuma alteração detectada");
        return;
      }

      const res = await fetch(`/api/apps/${appId}/bot/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar perfil");
      }

      const data = await res.json();
      setProfile(data);
      
      addToast({
        title: "Perfil atualizado",
        description: "As alterações foram aplicadas com sucesso",
        color: "success",
      });

      setIsModalOpen(false);
      setAvatarFile(null);
      setBannerFile(null);
      setAvatarPreview(null);
      setBannerPreview(null);
      onUpdate();
    } catch (err: any) {
      setError(err.message || "Erro ao atualizar perfil");
    } finally {
      setLoading(false);
    }
  };

  if (!tokenConfigured) {
    return (
      <div className="rounded-md bg-foreground/5 border border-foreground/10 p-4 text-center text-sm text-foreground/50">
        Configure o token primeiro
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="font-semibold flex items-center gap-2">
          <FontAwesomeIcon icon={faRobot} />
          Perfil do Bot
        </p>
        <Button
          size="sm"
          variant="flat"
          startContent={<FontAwesomeIcon icon={faEdit} />}
          onPress={() => setIsModalOpen(true)}
          isDisabled={!profile}
        >
          Editar
        </Button>
      </div>

      {profile && (
        <div className="relative">
          {/* Banner */}
          <div 
            className="h-24 rounded-t-lg bg-gradient-to-r from-primary to-secondary"
            style={profile.banner ? {
              backgroundImage: `url(${profile.banner})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center'
            } : {}}
          />
          
          {/* Avatar e Info */}
          <div className="flex items-end gap-4 px-4 -mt-10">
            <Avatar
              src={profile.avatar || undefined}
              name={profile.username}
              size="lg"
              className="border-4 border-background"
              showFallback
            />
            <div className="flex-1 pb-2">
              <p className="text-lg font-bold">{profile.username}</p>
              <p className="text-sm text-foreground/50">#{profile.discriminator}</p>
            </div>
          </div>
        </div>
      )}

      {/* Modal de edição */}
      <Modal isOpen={isModalOpen} onOpenChange={setIsModalOpen} size="lg">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader>Editar Perfil do Bot</ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  {error && (
                    <div className="rounded-md bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
                      {error}
                    </div>
                  )}

                  {/* Preview Banner */}
                  <div className="relative">
                    <div 
                      className="h-32 rounded-lg bg-gradient-to-r from-primary to-secondary cursor-pointer hover:opacity-80 transition-opacity"
                      style={bannerPreview || profile?.banner ? {
                        backgroundImage: `url(${bannerPreview || profile?.banner})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center'
                      } : {}}
                      onClick={() => bannerInputRef.current?.click()}
                    >
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-lg">
                        <FontAwesomeIcon icon={faPanorama} className="text-white text-2xl" />
                      </div>
                    </div>
                    <input
                      ref={bannerInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/gif"
                      onChange={handleBannerChange}
                      className="hidden"
                    />
                  </div>

                  {/* Preview Avatar */}
                  <div className="flex items-center gap-4">
                    <div 
                      className="relative cursor-pointer group"
                      onClick={() => avatarInputRef.current?.click()}
                    >
                      <Avatar
                        src={avatarPreview || profile?.avatar || undefined}
                        name={profile?.username}
                        size="lg"
                        showFallback
                        className="group-hover:opacity-80 transition-opacity"
                      />
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                        <FontAwesomeIcon icon={faImage} className="text-white" />
                      </div>
                    </div>
                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/gif"
                      onChange={handleAvatarChange}
                      className="hidden"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium">Avatar</p>
                      <p className="text-xs text-foreground/50">PNG, JPG ou GIF (máx. 8MB)</p>
                    </div>
                  </div>

                  {/* Username */}
                  <Input
                    label="Nome do Bot"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    description="Você pode alterar o nome do bot 2 vezes por hora"
                  />

                  <p className="text-foreground/50 text-xs">
                    As alterações podem levar alguns minutos para aparecer no Discord.
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
                  Salvar Alterações
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
}
