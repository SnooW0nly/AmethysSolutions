"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { useAppInfo } from "@/hooks/useApp";
import { Loading } from "@/components/Loading";
import { Button, Input, addToast, Avatar, Tabs, Tab } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { 
  faPalette, 
  faRobot, 
  faCircle, 
  faPaintBrush,
  faImage,
  faPanorama,
  faEye
} from "@fortawesome/free-solid-svg-icons";

interface CustomizationData {
  colors: {
    primary: string;
    secondary: string;
    success: string;
    danger: string;
    warning: string;
  };
  status: {
    type: string;
    names: string[];
  };
  mode: string;
  profile: {
    username: string;
    discriminator: string;
    avatar: string | null;
    banner: string | null;
  } | null;
}

export default function CustomizationPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id as string | undefined;
  const { app, loading: appLoading } = useAppInfo(id);
  
  const [customization, setCustomization] = useState<CustomizationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Profile states
  const [newUsername, setNewUsername] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [avatarUrl, setAvatarUrl] = useState("");
  const [bannerUrl, setBannerUrl] = useState("");
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);
  
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);
  
  // Colors states
  const [colors, setColors] = useState({
    primary: "",
    secondary: "",
    success: "",
    danger: "",
    warning: "",
  });
  
  // Status states
  const [statusType, setStatusType] = useState("online");
  const [statusNames, setStatusNames] = useState<string[]>(["", "", "", "", ""]);
  
  // Mode state
  const [displayMode, setDisplayMode] = useState("components");

  // Fetch customization data
  useEffect(() => {
    if (!id) return;
    
    const fetchCustomization = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/apps/${id}/customization`);
        if (!res.ok) throw new Error("Erro ao buscar personalização");
        
        const data = await res.json();
        setCustomization(data);
        
        // Set states
        if (data.profile) {
          setNewUsername(data.profile.username);
        }
        setColors(data.colors);
        setStatusType(data.status.type);
        const names = [...data.status.names];
        while (names.length < 5) names.push("");
        setStatusNames(names);
        setDisplayMode(data.mode);
      } catch (err: any) {
        addToast({
          title: "Erro",
          description: err.message || "Erro ao carregar personalização",
          color: "danger",
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchCustomization();
  }, [id]);

  // File to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        resolve(base64);
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
        addToast({
          title: "Erro",
          description: "Avatar deve ter no máximo 8MB",
          color: "danger",
        });
        return;
      }
      setAvatarFile(file);
      const url = URL.createObjectURL(file);
      setAvatarPreview(url);
    }
  };

  // Handle banner upload
  const handleBannerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 8 * 1024 * 1024) {
        addToast({
          title: "Erro",
          description: "Banner deve ter no máximo 8MB",
          color: "danger",
        });
        return;
      }
      setBannerFile(file);
      const url = URL.createObjectURL(file);
      setBannerPreview(url);
    }
  };

  // Save profile
  const handleSaveProfile = async () => {
    try {
      setSaving(true);
      const updates: any = {};

      if (newUsername && newUsername !== customization?.profile?.username) {
        updates.username = newUsername;
      }

      // Prioriza arquivo, depois URL
      if (avatarFile) {
        updates.avatar = await fileToBase64(avatarFile);
      } else if (avatarUrl && avatarUrl.trim()) {
        updates.avatar = avatarUrl.trim();
      }

      if (bannerFile) {
        updates.banner = await fileToBase64(bannerFile);
      } else if (bannerUrl && bannerUrl.trim()) {
        updates.banner = bannerUrl.trim();
      }

      if (Object.keys(updates).length === 0) {
        addToast({
          title: "Aviso",
          description: "Nenhuma alteração detectada",
          color: "warning",
        });
        return;
      }

      const res = await fetch(`/api/apps/${id}/customization/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar perfil");
      }

      const data = await res.json();
      setCustomization(prev => prev ? { ...prev, profile: data.profile } : null);
      setAvatarFile(null);
      setBannerFile(null);
      setAvatarUrl("");
      setBannerUrl("");
      setAvatarPreview(null);
      setBannerPreview(null);
      
      addToast({
        title: "Perfil atualizado",
        description: "As alterações foram aplicadas com sucesso",
        color: "success",
      });
    } catch (err: any) {
      addToast({
        title: "Erro",
        description: err.message || "Erro ao atualizar perfil",
        color: "danger",
      });
    } finally {
      setSaving(false);
    }
  };

  // Save colors
  const handleSaveColors = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/apps/${id}/customization/colors`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(colors),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar cores");
      }

      const data = await res.json();
      setCustomization(prev => prev ? { ...prev, colors: data.colors } : null);
      
      addToast({
        title: "Cores atualizadas",
        description: "As cores foram salvas com sucesso",
        color: "success",
      });
    } catch (err: any) {
      addToast({
        title: "Erro",
        description: err.message || "Erro ao atualizar cores",
        color: "danger",
      });
    } finally {
      setSaving(false);
    }
  };

  // Save status
  const handleSaveStatus = async () => {
    try {
      setSaving(true);
      const filteredNames = statusNames.filter(n => n && n.trim());
      
      const res = await fetch(`/api/apps/${id}/customization/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: statusType,
          names: filteredNames,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar status");
      }

      const data = await res.json();
      setCustomization(prev => prev ? { ...prev, status: data.status } : null);
      
      addToast({
        title: "Status atualizado",
        description: "O status foi salvo com sucesso",
        color: "success",
      });
    } catch (err: any) {
      addToast({
        title: "Erro",
        description: err.message || "Erro ao atualizar status",
        color: "danger",
      });
    } finally {
      setSaving(false);
    }
  };

  // Save mode
  const handleSaveMode = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/apps/${id}/customization/mode`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: displayMode }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Erro ao atualizar modo");
      }

      const data = await res.json();
      setCustomization(prev => prev ? { ...prev, mode: data.mode } : null);
      
      addToast({
        title: "Modo atualizado",
        description: "O modo de exibição foi salvo com sucesso",
        color: "success",
      });
    } catch (err: any) {
      addToast({
        title: "Erro",
        description: err.message || "Erro ao atualizar modo",
        color: "danger",
      });
    } finally {
      setSaving(false);
    }
  };

  if (appLoading || loading) return <Loading />;
  if (!app) return null;

  if (!app.bot?.configured) {
    return (
      <main className="p-5 md:p-10 flex flex-col gap-6 min-h-screen">
        <div className="flex flex-col gap-1">
          <p className="text-2xl font-bold">Personalização</p>
          <p className="text-foreground/60 text-sm">Personalize a aparência e comportamento do seu bot</p>
        </div>
        
        <div className="bg-background border border-foreground/10 rounded-xl p-8 text-center">
          <p className="text-foreground/50">Configure o token do bot primeiro para acessar as opções de personalização</p>
        </div>
      </main>
    );
  }

  return (
    <main className="p-5 md:p-10 flex flex-col gap-6 min-h-screen">
      <div className="flex flex-col gap-1">
        <p className="text-2xl font-bold">Personalização</p>
        <p className="text-foreground/60 text-sm">Personalize a aparência e comportamento do seu bot</p>
      </div>

      <Tabs aria-label="Opções de personalização" color="primary" variant="underlined">
        {/* Tab: Perfil */}
        <Tab
          key="profile"
          title={
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faRobot} />
              <span>Perfil</span>
            </div>
          }
        >
          <div className="bg-background border border-foreground/10 rounded-xl p-6 mt-4">
            <div className="flex flex-col gap-6">
              {/* Preview do perfil */}
              {customization?.profile && (
                <div className="relative">
                  {/* Banner */}
                  <div 
                    className="h-32 rounded-t-lg bg-gradient-to-r from-primary to-secondary cursor-pointer hover:opacity-90 transition-opacity relative group"
                    style={bannerPreview || customization.profile.banner ? {
                      backgroundImage: `url(${bannerPreview || customization.profile.banner})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center'
                    } : {}}
                    onClick={() => bannerInputRef.current?.click()}
                  >
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-t-lg opacity-0 group-hover:opacity-100 transition-opacity">
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
                  
                  {/* Avatar e Info */}
                  <div className="flex items-end gap-4 px-4 -mt-12">
                    <div 
                      className="relative cursor-pointer group"
                      onClick={() => avatarInputRef.current?.click()}
                    >
                      <Avatar
                        src={avatarPreview || customization.profile.avatar || undefined}
                        name={customization.profile.username}
                        size="lg"
                        className="border-4 border-background group-hover:opacity-80 transition-opacity"
                        showFallback
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
                    <div className="flex-1 pb-2">
                      <p className="text-lg font-bold">{customization.profile.username}</p>
                      <p className="text-sm text-foreground/50">#{customization.profile.discriminator}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Nome do bot */}
              <Input
                label="Nome do Bot"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                description="Você pode alterar o nome do bot 2 vezes por hora"
              />

              {/* URL do Avatar */}
              <Input
                label="URL do Avatar (opcional)"
                placeholder="https://exemplo.com/avatar.png"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                description="Cole a URL de uma imagem ou clique no avatar acima para fazer upload"
              />

              {/* URL do Banner */}
              <Input
                label="URL do Banner (opcional)"
                placeholder="https://exemplo.com/banner.png"
                value={bannerUrl}
                onChange={(e) => setBannerUrl(e.target.value)}
                description="Cole a URL de uma imagem ou clique no banner acima para fazer upload"
              />

              <p className="text-foreground/50 text-xs">
                Você pode fazer upload de arquivos clicando nas imagens ou colar URLs nos campos acima. As alterações podem levar alguns minutos para aparecer no Discord.
              </p>

              <Button
                color="primary"
                onPress={handleSaveProfile}
                isLoading={saving}
                className="w-full md:w-auto"
              >
                Salvar Perfil
              </Button>
            </div>
          </div>
        </Tab>

        {/* Tab: Cores */}
        <Tab
          key="colors"
          title={
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faPaintBrush} />
              <span>Cores</span>
            </div>
          }
        >
          <div className="bg-background border border-foreground/10 rounded-xl p-6 mt-4">
            <div className="flex flex-col gap-6">
              <p className="text-sm text-foreground/60">Configure as cores utilizadas pelo seu bot</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-lg border-2 border-foreground/20"
                    style={{ backgroundColor: colors.primary || "#5c5ef0" }}
                  />
                  <Input
                    label="Cor Primária"
                    placeholder="#5c5ef0"
                    value={colors.primary}
                    onChange={(e) => setColors({ ...colors, primary: e.target.value })}
                    maxLength={7}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-lg border-2 border-foreground/20"
                    style={{ backgroundColor: colors.secondary || "#6c757d" }}
                  />
                  <Input
                    label="Cor Secundária"
                    placeholder="#6c757d"
                    value={colors.secondary}
                    onChange={(e) => setColors({ ...colors, secondary: e.target.value })}
                    maxLength={7}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-lg border-2 border-foreground/20"
                    style={{ backgroundColor: colors.success || "#28a745" }}
                  />
                  <Input
                    label="Cor de Sucesso"
                    placeholder="#28a745"
                    value={colors.success}
                    onChange={(e) => setColors({ ...colors, success: e.target.value })}
                    maxLength={7}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-lg border-2 border-foreground/20"
                    style={{ backgroundColor: colors.danger || "#dc3545" }}
                  />
                  <Input
                    label="Cor de Perigo"
                    placeholder="#dc3545"
                    value={colors.danger}
                    onChange={(e) => setColors({ ...colors, danger: e.target.value })}
                    maxLength={7}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div 
                    className="w-12 h-12 rounded-lg border-2 border-foreground/20"
                    style={{ backgroundColor: colors.warning || "#ffc107" }}
                  />
                  <Input
                    label="Cor de Aviso"
                    placeholder="#ffc107"
                    value={colors.warning}
                    onChange={(e) => setColors({ ...colors, warning: e.target.value })}
                    maxLength={7}
                  />
                </div>
              </div>

              <Button
                color="primary"
                onPress={handleSaveColors}
                isLoading={saving}
                className="w-full md:w-auto"
              >
                Salvar Cores
              </Button>
            </div>
          </div>
        </Tab>

        {/* Tab: Status */}
        <Tab
          key="status"
          title={
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faCircle} />
              <span>Status</span>
            </div>
          }
        >
          <div className="bg-background border border-foreground/10 rounded-xl p-6 mt-4">
            <div className="flex flex-col gap-6">
              <p className="text-sm text-foreground/60">Configure o status do seu bot no Discord</p>

              {/* Tipo de status */}
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">Tipo de Status</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {[
                    { value: "online", label: "Online", color: "success" },
                    { value: "idle", label: "Ausente", color: "warning" },
                    { value: "dnd", label: "Não Perturbar", color: "danger" },
                    { value: "streaming", label: "Transmitindo", color: "secondary" },
                  ].map((status) => (
                    <Button
                      key={status.value}
                      variant={statusType === status.value ? "solid" : "bordered"}
                      color={statusType === status.value ? status.color as any : "default"}
                      onPress={() => setStatusType(status.value)}
                      className="w-full"
                    >
                      {status.label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Nomes do status */}
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium">Nomes do Status (Rotativo)</label>
                {statusNames.map((name, index) => (
                  <Input
                    key={index}
                    label={`Status #${index + 1}`}
                    placeholder={index === 0 ? "Deixe em branco para não ter status" : "Deixe em branco para não usar"}
                    value={name}
                    onChange={(e) => {
                      const newNames = [...statusNames];
                      newNames[index] = e.target.value;
                      setStatusNames(newNames);
                    }}
                    maxLength={100}
                  />
                ))}
                <p className="text-xs text-foreground/50">
                  Configure até 5 nomes que serão alternados automaticamente
                </p>
              </div>

              <Button
                color="primary"
                onPress={handleSaveStatus}
                isLoading={saving}
                className="w-full md:w-auto"
              >
                Salvar Status
              </Button>
            </div>
          </div>
        </Tab>

        {/* Tab: Modo de Exibição */}
        <Tab
          key="mode"
          title={
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faEye} />
              <span>Modo</span>
            </div>
          }
        >
          <div className="bg-background border border-foreground/10 rounded-xl p-6 mt-4">
            <div className="flex flex-col gap-6">
              <p className="text-sm text-foreground/60">Selecione o modo de exibição do bot</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  variant={displayMode === "embed" ? "solid" : "bordered"}
                  color={displayMode === "embed" ? "primary" : "default"}
                  onPress={() => setDisplayMode("embed")}
                  className="h-auto py-4 flex-col items-start"
                >
                  <p className="font-semibold">Componentes V1</p>
                  <p className="text-xs text-left">Modo de exibição antigo com Embeds</p>
                </Button>

                <Button
                  variant={displayMode === "components" ? "solid" : "bordered"}
                  color={displayMode === "components" ? "primary" : "default"}
                  onPress={() => setDisplayMode("components")}
                  className="h-auto py-4 flex-col items-start"
                >
                  <p className="font-semibold">Componentes V2</p>
                  <p className="text-xs text-left">Modo de exibição novo com Containers</p>
                </Button>
              </div>

              <Button
                color="primary"
                onPress={handleSaveMode}
                isLoading={saving}
                className="w-full md:w-auto"
              >
                Salvar Modo
              </Button>
            </div>
          </div>
        </Tab>
      </Tabs>
    </main>
  );
}
