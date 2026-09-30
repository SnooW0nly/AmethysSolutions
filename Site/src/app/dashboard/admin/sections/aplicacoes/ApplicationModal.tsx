"use client";

import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Textarea,
  Switch,
  Tabs,
  Tab,
  Card,
  CardBody,
  Chip,
  Divider,
  Code,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faServer,
  faUser,
  faClock,
  faMemory,
  faCode,
  faShieldAlt,
  faDatabase,
  faExclamationTriangle,
  faSave,
  faTrash,
  faRotate,
  faPlay,
  faStop,
  faBan,
  faEye,
  faEyeSlash,
  faRocket,          // ← ícone do redeploy
  faCircleCheck,
} from "@fortawesome/free-solid-svg-icons";
import { Application } from "@/types/application";

interface ApplicationModalProps {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onAction: (action: string, data?: any) => Promise<boolean>;
}

// ─── Estado local do Redeploy ─────────────────────────────────────────────────

type RedeployState =
  | { phase: "idle" }
  | { phase: "confirm" }
  | { phase: "loading" }
  | { phase: "success"; message: string; newAppId?: string }
  | { phase: "error"; message: string };

export function ApplicationModal({ application, isOpen, onClose, onAction }: ApplicationModalProps) {
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    name: application.name,
    expiresAt: application.expiresAt ? new Date(application.expiresAt).toISOString().split("T")[0] : "",
    isBlocked: application.isBlocked || false,
    canRecover: application.canRecover !== false,
    ram: application.hosting?.ram || 200,
    bot: {
      token: application.bot?.token || "",
      owner: application.bot?.owner || "",
      id: application.bot?.id || "",
      server: application.bot?.server || "",
      perms: application.bot?.perms || [],
    },
    plan: {
      id: application.plan?.id || "",
      name: application.plan?.name || "",
      price: application.plan?.price || 0,
      months: application.plan?.months || 1,
    },
  });
  const [showToken, setShowToken] = useState(false);
  const [newPerm, setNewPerm] = useState("");
  const [loading, setLoading] = useState(false);

  // Redeploy
  const [redeploy, setRedeploy] = useState<RedeployState>({ phase: "idle" });

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const hasAppId = !!application.hosting?.appId;

  const handleSave = async () => {
    setLoading(true);
    const updateData = {
      name: formData.name,
      expiresAt: formData.expiresAt,
      isBlocked: formData.isBlocked,
      canRecover: formData.canRecover,
      bot: formData.bot,
      plan: formData.plan,
    };
    const success = await onAction("update", updateData);
    if (success) setEditMode(false);
    setLoading(false);
  };

  const handleAction = async (action: string) => {
    setLoading(true);
    await onAction(action);
    setLoading(false);
  };

  const handleRamChange = async () => {
    setLoading(true);
    await onAction("changeRam", { ram: formData.ram });
    setLoading(false);
  };

  // ── Redeploy ─────────────────────────────────────────────────────────────────

  const startRedeploy = () => setRedeploy({ phase: "confirm" });
  const cancelRedeploy = () => setRedeploy({ phase: "idle" });

  const confirmRedeploy = async () => {
    setRedeploy({ phase: "loading" });
    try {
      const res = await fetch(`/api/admin/applications/${application._id}/redeploy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await res.json();

      if (!res.ok) {
        setRedeploy({ phase: "error", message: data.error || "Erro ao fazer redeploy" });
        return;
      }

      setRedeploy({
        phase: "success",
        message: data.message,
        newAppId: data.details?.newAppId,
      });
    } catch (err: any) {
      setRedeploy({ phase: "error", message: err.message || "Erro de conexão" });
    }
  };

  // ── Render do banner de Redeploy ──────────────────────────────────────────

  const renderRedeployBanner = () => {
    // Aparece sempre que não há appId (deploy original falhou) OU se o admin abriu o confirm
    if (redeploy.phase === "idle" && hasAppId) return null;

    // Aviso passivo quando não tem appId
    if (redeploy.phase === "idle" && !hasAppId) {
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-warning/8 border border-warning/25">
          <FontAwesomeIcon icon={faExclamationTriangle} className="text-warning text-sm mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-warning-700">Aplicação sem hospedagem na Stackr</p>
            <p className="text-xs text-foreground/60 mt-0.5">
              Essa aplicação foi registrada no banco mas o deploy na Stackr não foi concluído.
              Clique em <strong>Redeploy</strong> no rodapé para subir o bot usando o ZIP do plano{" "}
              <code className="bg-foreground/10 px-1 rounded">{application.plan?.name}</code>.
            </p>
          </div>
        </div>
      );
    }

    // Confirmação
    if (redeploy.phase === "confirm") {
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-primary/6 border border-primary/25">
          <FontAwesomeIcon icon={faRocket} className="text-primary text-sm mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0space-y-1">
            <p className="text-sm font-medium">Confirmar Redeploy?</p>
            <p className="text-xs text-foreground/60 mt-0.5">
              Será feito um novo deploy usando o ZIP do plano{" "}
              <strong>{application.plan?.name}</strong>. Todos os dados existentes (token, dono, permissões, expiração) serão preservados.
              Apenas o <code className="bg-foreground/10 px-1 rounded">hosting</code> será atualizado com as infos da Stackr.
            </p>
            <div className="flex gap-2 mt-2">
              <Button size="sm" color="primary" onPress={confirmRedeploy} startContent={<FontAwesomeIcon icon={faRocket} />}>
                Confirmar Deploy
              </Button>
              <Button size="sm" variant="light" onPress={cancelRedeploy}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      );
    }

    // Loading
    if (redeploy.phase === "loading") {
      return (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-foreground/5 border border-foreground/10">
          <FontAwesomeIcon icon={faRotate} className="animate-spin text-primary text-sm shrink-0" />
          <p className="text-sm text-foreground/70">Fazendo deploy na Stackr… Aguarde.</p>
        </div>
      );
    }

    // Sucesso
    if (redeploy.phase === "success") {
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-success/8 border border-success/25">
          <FontAwesomeIcon icon={faCircleCheck} className="text-success text-sm mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-success-700">Deploy realizado com sucesso!</p>
            <p className="text-xs text-foreground/60 mt-0.5">{redeploy.message}</p>
            {redeploy.newAppId && (
              <p className="text-xs mt-1">
                <span className="text-foreground/50">Novo App ID Stackr: </span>
                <code className="bg-foreground/10 px-1 rounded font-mono">{redeploy.newAppId}</code>
              </p>
            )}
          </div>
        </div>
      );
    }

    // Erro
    if (redeploy.phase === "error") {
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-danger/8 border border-danger/25">
          <FontAwesomeIcon icon={faExclamationTriangle} className="text-danger text-sm mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-danger-700">Erro no deploy</p>
            <p className="text-xs text-foreground/60 mt-0.5">{redeploy.message}</p>
            <Button size="sm" variant="flat" color="danger" className="mt-2" onPress={() => setRedeploy({ phase: "confirm" })}>
              Tentar novamente
            </Button>
          </div>
        </div>
      );
    }

    return null;
  };

  // ── JSX principal ─────────────────────────────────────────────────────────

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="3xl" scrollBehavior="inside">
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader className="flex justify-between items-center">
              <span>Detalhes da Aplicação</span>
              <div className="flex items-center gap-2">
                {!editMode ? (
                  <Button size="sm" variant="light" onPress={() => setEditMode(true)}>
                    Editar
                  </Button>
                ) : (
                  <>
                    <Button size="sm" variant="light" onPress={() => setEditMode(false)}>
                      Cancelar
                    </Button>
                    <Button
                      size="sm"
                      color="primary"
                      onPress={handleSave}
                      isLoading={loading}
                      startContent={<FontAwesomeIcon icon={faSave} />}
                    >
                      Salvar
                    </Button>
                  </>
                )}
              </div>
            </ModalHeader>

            <ModalBody>
              {/* Banner de Redeploy — aparece no topo do body */}
              {renderRedeployBanner() && (
                <div className="mb-2">{renderRedeployBanner()}</div>
              )}

              <Tabs aria-label="Detalhes">
                <Tab key="general" title="Geral">
                  <Card>
                    <CardBody className="space-y-4">
                      {/* Informações básicas */}
                      <div>
                        <h4 className="font-semibold mb-2">Informações Básicas</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <Input
                            label="Nome"
                            value={editMode ? formData.name : application.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                          <Input
                            label="Bot ID"
                            value={application.botID || "-"}
                            isReadOnly
                            size="sm"
                          />
                          <Input
                            label="ID MongoDB"
                            value={application._id}
                            isReadOnly
                            size="sm"
                          />
                          <Input
                            label="Data de Expiração"
                            type="date"
                            value={
                              editMode
                                ? formData.expiresAt
                                : application.expiresAt
                                ? new Date(application.expiresAt).toISOString().split("T")[0]
                                : ""
                            }
                            onChange={(e) => setFormData({ ...formData, expiresAt: e.target.value })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                        </div>
                      </div>

                      <Divider />

                      {/* Status */}
                      <div>
                        <h4 className="font-semibold mb-2">Status</h4>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Bloqueado</span>
                            <Switch
                              isSelected={editMode ? formData.isBlocked : application.isBlocked}
                              onValueChange={(v) => setFormData({ ...formData, isBlocked: v })}
                              isDisabled={!editMode}
                              size="sm"
                            />
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm">Pode Recuperar</span>
                            <Switch
                              isSelected={editMode ? formData.canRecover : application.canRecover !== false}
                              onValueChange={(v) => setFormData({ ...formData, canRecover: v })}
                              isDisabled={!editMode}
                              size="sm"
                            />
                          </div>
                        </div>
                      </div>

                      <Divider />

                      {/* Plano */}
                      <div>
                        <h4 className="font-semibold mb-2">Plano</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <Input
                            label="ID do Plano"
                            value={editMode ? formData.plan.id : (application.plan?.id || "")}
                            onChange={(e) => setFormData({ ...formData, plan: { ...formData.plan, id: e.target.value } })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                          <Input
                            label="Nome do Plano"
                            value={editMode ? formData.plan.name : (application.plan?.name || "")}
                            onChange={(e) => setFormData({ ...formData, plan: { ...formData.plan, name: e.target.value } })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                          <Input
                            label="Preço"
                            type="number"
                            value={String(editMode ? formData.plan.price : (application.plan?.price || 0))}
                            onChange={(e) => setFormData({ ...formData, plan: { ...formData.plan, price: Number(e.target.value) } })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                          <Input
                            label="Meses"
                            type="number"
                            value={String(editMode ? formData.plan.months : (application.plan?.months || 1))}
                            onChange={(e) => setFormData({ ...formData, plan: { ...formData.plan, months: Number(e.target.value) } })}
                            isReadOnly={!editMode}
                            size="sm"
                          />
                        </div>
                      </div>

                      <Divider />

                      {/* Hosting */}
                      <div>
                        <h4 className="font-semibold mb-2">Hospedagem</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <Input
                            label="App ID (Stackr)"
                            value={application.hosting?.appId || ""}
                            isReadOnly
                            size="sm"
                            color={!application.hosting?.appId ? "warning" : "default"}
                            description={!application.hosting?.appId ? "Sem appId — use o Redeploy" : undefined}
                          />
                          <Input
                            label="Status"
                            value={application.hosting?.status || "-"}
                            isReadOnly
                            size="sm"
                          />
                          {application.hosting?.appId && (
                            <>
                              <Input
                                label="RAM (MB)"
                                type="number"
                                value={String(editMode ? formData.ram : (application.hosting?.ram || 200))}
                                onChange={(e) => setFormData({ ...formData, ram: Number(e.target.value) })}
                                isReadOnly={!editMode}
                                size="sm"
                              />
                              {editMode && (
                                <div className="flex items-end">
                                  <Button size="sm" color="primary" onPress={handleRamChange} isLoading={loading}>
                                    Alterar RAM
                                  </Button>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </Tab>

                <Tab key="bot" title="Bot">
                  <Card>
                    <CardBody className="space-y-4">
                      <h4 className="font-semibold">Configuração do Bot</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {/* Token */}
                        <div className="col-span-full">
                          <Input
                            label="Token"
                            type={showToken ? "text" : "password"}
                            value={editMode ? formData.bot.token : (application.bot?.token || "")}
                            onChange={(e) => setFormData({ ...formData, bot: { ...formData.bot, token: e.target.value } })}
                            isReadOnly={!editMode}
                            size="sm"
                            endContent={
                              <button onClick={() => setShowToken(!showToken)}>
                                <FontAwesomeIcon icon={showToken ? faEyeSlash : faEye} className="text-foreground/40" />
                              </button>
                            }
                          />
                        </div>
                        <Input
                          label="Owner (Discord ID)"
                          value={editMode ? formData.bot.owner : (application.bot?.owner || "")}
                          onChange={(e) => setFormData({ ...formData, bot: { ...formData.bot, owner: e.target.value } })}
                          isReadOnly={!editMode}
                          size="sm"
                        />
                        <Input
                          label="Bot ID (Discord)"
                          value={editMode ? formData.bot.id : (application.bot?.id || "")}
                          onChange={(e) => setFormData({ ...formData, bot: { ...formData.bot, id: e.target.value } })}
                          isReadOnly={!editMode}
                          size="sm"
                          placeholder="ID do bot no Discord"
                        />
                        <Input
                          label="Server ID"
                          value={editMode ? formData.bot.server : (application.bot?.server || "")}
                          onChange={(e) => setFormData({ ...formData, bot: { ...formData.bot, server: e.target.value } })}
                          isReadOnly={!editMode}
                          size="sm"
                          placeholder="ID do servidor principal"
                        />
                      </div>

                      <Divider />

                      <div>
                        <h5 className="font-medium mb-2">Permissões (Discord IDs)</h5>
                        {editMode ? (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Input
                                value={newPerm}
                                onChange={(e) => setNewPerm(e.target.value)}
                                placeholder="Discord ID para adicionar permissão"
                                size="sm"
                              />
                              <Button
                                size="sm"
                                color="primary"
                                onPress={() => {
                                  if (newPerm && !formData.bot.perms.includes(newPerm)) {
                                    setFormData({
                                      ...formData,
                                      bot: { ...formData.bot, perms: [...formData.bot.perms, newPerm] },
                                    });
                                    setNewPerm("");
                                  }
                                }}
                              >
                                Adicionar
                              </Button>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {formData.bot.perms.map((perm: string, idx: number) => (
                                <Chip
                                  key={idx}
                                  size="sm"
                                  variant="flat"
                                  onClose={() =>
                                    setFormData({
                                      ...formData,
                                      bot: {
                                        ...formData.bot,
                                        perms: formData.bot.perms.filter((_: string, i: number) => i !== idx),
                                      },
                                    })
                                  }
                                >
                                  {perm}
                                </Chip>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {(application.bot?.perms || []).map((perm: string, idx: number) => (
                              <Chip key={idx} size="sm" variant="flat">
                                {perm}
                              </Chip>
                            ))}
                          </div>
                        )}
                      </div>

                      {application.botConfig && (
                        <>
                          <Divider />
                          <div>
                            <h5 className="font-medium mb-2">Bot Config</h5>
                            <div className="space-y-2 text-sm">
                              <div>
                                <span className="text-foreground/60">Bot Token: </span>
                                <Code>{application.botConfig.botToken}</Code>
                              </div>
                              <div>
                                <span className="text-foreground/60">API URL: </span>
                                <p>{application.botConfig.apiURL}</p>
                              </div>
                              <div>
                                <span className="text-foreground/60">Versão: </span>
                                <p>{application.botConfig.version}</p>
                              </div>
                            </div>
                          </div>
                        </>
                      )}
                    </CardBody>
                  </Card>
                </Tab>

                <Tab key="user" title="Usuário">
                  <Card>
                    <CardBody className="space-y-4">
                      <h4 className="font-semibold">Informações do Proprietário</h4>

                      {application.userId ? (
                        <div className="space-y-3">
                          <div className="flex items-center gap-4">
                            {application.userId.avatar && (
                              <img
                                src={application.userId.avatar}
                                alt={application.userId.username}
                                className="w-16 h-16 rounded-full"
                              />
                            )}
                            <div>
                              <h5 className="font-medium">{application.userId.username || "Usuário"}</h5>
                              <p className="text-sm text-foreground/60">{application.userId.email}</p>
                              <p className="text-xs text-foreground/50">ID: {application.userId._id}</p>
                            </div>
                          </div>

                          <Divider />

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <span className="text-foreground/60">Criado em:</span>
                              <p>{new Date(application.createdAt).toLocaleDateString("pt-BR")}</p>
                            </div>
                            <div>
                              <span className="text-foreground/60">Atualizado em:</span>
                              <p>{new Date(application.updatedAt).toLocaleDateString("pt-BR")}</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-foreground/60">Sem informações do usuário</p>
                      )}
                    </CardBody>
                  </Card>
                </Tab>
              </Tabs>
            </ModalBody>

            <ModalFooter>
              <div className="flex justify-between items-center w-full">
                <div className="flex gap-2 flex-wrap">
                  {/* ── Redeploy ── aparece sempre que não tem appId OU se está em confirm/erro */}
                  {(!hasAppId || redeploy.phase === "confirm" || redeploy.phase === "error") &&
                    redeploy.phase !== "loading" &&
                    redeploy.phase !== "success" && (
                      <Button
                        color="secondary"
                        variant="flat"
                        size="sm"
                        onPress={redeploy.phase === "idle" ? startRedeploy : confirmRedeploy}
                        isLoading={redeploy.phase === "loading"}
                        startContent={<FontAwesomeIcon icon={faRocket} />}
                      >
                        {redeploy.phase === "confirm" ? "Confirmar Redeploy" : "Redeploy"}
                      </Button>
                    )}

                  {/* ── Forçar Redeploy (quando já tem appId, fica discreto) ── */}
                  {hasAppId &&
                    redeploy.phase === "idle" && (
                      <Button
                        color="default"
                        variant="light"
                        size="sm"
                        onPress={startRedeploy}
                        startContent={<FontAwesomeIcon icon={faRocket} />}
                        className="text-foreground/50"
                      >
                        Forçar Redeploy
                      </Button>
                    )}

                  <Divider orientation="vertical" className="h-6 self-center" />

                  {application.isBlocked ? (
                    <Button
                      color="success"
                      variant="flat"
                      size="sm"
                      onPress={() => handleAction("unblock")}
                      isLoading={loading}
                      startContent={<FontAwesomeIcon icon={faPlay} />}
                    >
                      Desbloquear
                    </Button>
                  ) : (
                    <Button
                      color="warning"
                      variant="flat"
                      size="sm"
                      onPress={() => handleAction("block")}
                      isLoading={loading}
                      startContent={<FontAwesomeIcon icon={faBan} />}
                    >
                      Bloquear
                    </Button>
                  )}

                  <Button
                    color="danger"
                    variant="flat"
                    size="sm"
                    onPress={() => {
                      if (confirm(`Tem certeza que deseja deletar ${application.name}?`)) {
                        handleAction("delete");
                      }
                    }}
                    isLoading={loading}
                    startContent={<FontAwesomeIcon icon={faTrash} />}
                  >
                    Deletar
                  </Button>
                </div>

                <Button color="primary" onPress={onClose}>
                  Fechar
                </Button>
              </div>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}
