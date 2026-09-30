"use client";

// src/app/dashboard/admin/sections/aplicacoes/ApplicationCard.tsx
// Adicionado: botão "Transferir Posse" no dropdown

import { useState } from "react";
import {
  Card,
  CardBody,
  CardFooter,
  Chip,
  Button,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faEllipsisV,
  faEye,
  faBan,
  faPlay,
  faStop,
  faRotate,
  faTrash,
  faUndo,
  faServer,
  faClock,
  faUser,
  faMemory,
  faExternalLinkAlt,
  faExchangeAlt,
} from "@fortawesome/free-solid-svg-icons";
import { Application } from "@/types/application";
import { TransferOwnerModal } from "./TransferOwnerModal";

interface ApplicationCardProps {
  application: Application;
  onView: () => void;
  onAction: (action: string, data?: any) => Promise<boolean>;
  onRefresh?: () => void;
}

export function ApplicationCard({
  application,
  onView,
  onAction,
  onRefresh,
}: ApplicationCardProps) {
  const [transferModalOpen, setTransferModalOpen] = useState(false);

  const isExpired =
    application.expiresAt && new Date(application.expiresAt) < new Date();
  const daysUntilExpiry = application.expiresAt
    ? Math.ceil(
        (new Date(application.expiresAt).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24)
      )
    : null;

  const handleAction = async (action: string) => {
    if (action === "delete") {
      const deleteFrom = prompt(
        `Deletar ${application.name} de onde?\n\n` +
          "Digite uma opção:\n" +
          "1 - Apenas Database (soft delete)\n" +
          "2 - Apenas Database (permanente)\n" +
          "3 - Apenas Discloud\n" +
          "4 - Database e Discloud\n" +
          "5 - Cancelar"
      );

      if (!deleteFrom || deleteFrom === "5") return;

      let options = {};
      switch (deleteFrom) {
        case "1":
          options = { deleteFrom: "database", permanent: false };
          break;
        case "2":
          options = { deleteFrom: "database", permanent: true };
          break;
        case "3":
          options = { deleteFrom: "starckr" };
          break;
        case "4":
          if (
            confirm(
              "Tem certeza? Isso removerá a aplicação permanentemente de ambos os lugares!"
            )
          ) {
            options = { deleteFrom: "both", permanent: true };
          } else {
            return;
          }
          break;
        default:
          return;
      }

      await onAction(action, options);
    } else {
      await onAction(action);
    }
  };

  return (
    <>
      <Card className="border border-foreground/10 bg-foreground/2 hover:bg-foreground/5 transition-all">
        <CardBody className="p-4">
          <div className="flex justify-between items-start mb-3">
            <div className="flex-1">
              <h4 className="font-semibold text-base">{application.name}</h4>
              <p className="text-xs text-foreground/60 mt-1">
                ID: {application.botID || application._id}
              </p>
            </div>
            <Dropdown>
              <DropdownTrigger>
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  className="text-foreground/60"
                >
                  <FontAwesomeIcon icon={faEllipsisV} />
                </Button>
              </DropdownTrigger>
              <DropdownMenu aria-label="Ações">
                <DropdownItem
                  key="view"
                  startContent={<FontAwesomeIcon icon={faEye} />}
                  onPress={onView}
                >
                  Ver detalhes
                </DropdownItem>

                {/* Transferir Posse — sem email, direto no DB */}
                <DropdownItem
                  key="transfer"
                  startContent={<FontAwesomeIcon icon={faExchangeAlt} />}
                  className="text-primary"
                  onPress={() => setTransferModalOpen(true)}
                >
                  Transferir Posse
                </DropdownItem>

                {application.hosting?.appId && (
                  <DropdownItem
                    key="starckr"
                    startContent={<FontAwesomeIcon icon={faExternalLinkAlt} />}
                    onPress={() =>
                      window.open(
                        `https://starckr.com/dashboard/app/${application.hosting.appId}`,
                        "_blank"
                      )
                    }
                  >
                    Ver na Discloud
                  </DropdownItem>
                )}

                {!application.isBlocked ? (
                  <DropdownItem
                    key="block"
                    startContent={<FontAwesomeIcon icon={faBan} />}
                    className="text-warning"
                    onPress={() => handleAction("block")}
                  >
                    Bloquear
                  </DropdownItem>
                ) : (
                  <DropdownItem
                    key="unblock"
                    startContent={<FontAwesomeIcon icon={faPlay} />}
                    className="text-success"
                    onPress={() => handleAction("unblock")}
                  >
                    Desbloquear
                  </DropdownItem>
                )}

                {application.hosting?.appId && (
                  <>
                    <DropdownItem
                      key="restart"
                      startContent={<FontAwesomeIcon icon={faRotate} />}
                      onPress={() => handleAction("restart")}
                    >
                      Reiniciar
                    </DropdownItem>

                    {application.hosting?.status === "online" ? (
                      <DropdownItem
                        key="stop"
                        startContent={<FontAwesomeIcon icon={faStop} />}
                        className="text-danger"
                        onPress={() => handleAction("stop")}
                      >
                        Parar
                      </DropdownItem>
                    ) : (
                      <DropdownItem
                        key="start"
                        startContent={<FontAwesomeIcon icon={faPlay} />}
                        className="text-success"
                        onPress={() => handleAction("start")}
                      >
                        Iniciar
                      </DropdownItem>
                    )}
                  </>
                )}

                {application.isDeleted ? (
                  <DropdownItem
                    key="restore"
                    startContent={<FontAwesomeIcon icon={faUndo} />}
                    className="text-success"
                    onPress={() => handleAction("restore")}
                  >
                    Restaurar
                  </DropdownItem>
                ) : (
                  <DropdownItem
                    key="delete"
                    startContent={<FontAwesomeIcon icon={faTrash} />}
                    className="text-danger"
                    onPress={() => handleAction("delete")}
                  >
                    Deletar
                  </DropdownItem>
                )}
              </DropdownMenu>
            </Dropdown>
          </div>

          {/* Status e informações */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              {application.plan?.name && (
                <Chip size="sm" color="primary" variant="flat">
                  {application.plan.name}
                </Chip>
              )}

              {application.isBlocked && (
                <Chip size="sm" color="danger" variant="flat">
                  Bloqueado
                </Chip>
              )}

              {isExpired ? (
                <Chip size="sm" color="danger" variant="flat">
                  Expirado
                </Chip>
              ) : daysUntilExpiry !== null && daysUntilExpiry <= 7 ? (
                <Chip size="sm" color="warning" variant="flat">
                  Expira em {daysUntilExpiry}d
                </Chip>
              ) : null}
            </div>

            {application.userId && (
              <div className="flex items-center gap-2 text-xs text-foreground/70">
                <FontAwesomeIcon icon={faUser} className="text-foreground/50" />
                <span>
                  {application.userId.username ||
                    application.userId.email ||
                    "Usuário"}
                </span>
              </div>
            )}

            {application.hosting && (
              <div className="grid grid-cols-2 gap-2 text-xs text-foreground/70">
                {application.hosting.ram && (
                  <div className="flex items-center gap-1">
                    <FontAwesomeIcon
                      icon={faMemory}
                      className="text-foreground/50"
                    />
                    <span>{application.hosting.ram} MB</span>
                  </div>
                )}

                {application.hosting.appId && (
                  <div className="flex items-center gap-1">
                    <FontAwesomeIcon
                      icon={faServer}
                      className="text-foreground/50"
                    />
                    <span title={application.hosting.appId}>
                      {application.hosting.appId.substring(0, 8)}...
                    </span>
                  </div>
                )}
              </div>
            )}

            {application.expiresAt && (
              <div className="flex items-center gap-2 text-xs text-foreground/70">
                <FontAwesomeIcon
                  icon={faClock}
                  className="text-foreground/50"
                />
                <span>
                  Expira em{" "}
                  {new Date(application.expiresAt).toLocaleDateString("pt-BR")}
                </span>
              </div>
            )}
          </div>
        </CardBody>

        <CardFooter className="p-3 pt-0">
          <Button
            size="sm"
            color="primary"
            variant="flat"
            className="w-full"
            onPress={onView}
          >
            Ver detalhes
          </Button>
        </CardFooter>
      </Card>

      {/* Modal de transferência de posse */}
      <TransferOwnerModal
        application={application}
        isOpen={transferModalOpen}
        onClose={() => setTransferModalOpen(false)}
        onSuccess={() => {
          setTransferModalOpen(false);
          onRefresh?.();
        }}
      />
    </>
  );
}
