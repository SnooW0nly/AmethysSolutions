"use client";

import { Table, TableHeader, TableColumn, TableBody, TableRow, TableCell, Chip, Spinner } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { 
  faUser, 
  faServer, 
  faClock,
  faTag,
  faExclamationTriangle,
  faCheckCircle,
  faTimesCircle,
  faRotate,
  faPlay,
  faStop,
  faBan,
  faUndo,
  faTrash,
  faEdit,
  faMemory,
} from "@fortawesome/free-solid-svg-icons";

interface AuditLog {
  _id: string;
  entity: string;
  action: string;
  actorId: string;
  targetId: string;
  metadata: any;
  createdAt: string;
}

interface AuditTableProps {
  logs: AuditLog[];
  loading?: boolean;
}

export function AuditTable({ logs, loading }: AuditTableProps) {
  const getActionIcon = (action: string) => {
    switch (action) {
      case "create":
        return faCheckCircle;
      case "update":
        return faEdit;
      case "delete":
      case "delete_permanent":
      case "delete_soft":
        return faTrash;
      case "block":
        return faBan;
      case "unblock":
        return faPlay;
      case "restart":
        return faRotate;
      case "stop":
        return faStop;
      case "start":
        return faPlay;
      case "restore":
        return faUndo;
      case "change_ram":
        return faMemory;
      default:
        return faTag;
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case "create":
      case "start":
      case "unblock":
      case "restore":
        return "success";
      case "update":
      case "restart":
      case "change_ram":
        return "primary";
      case "delete":
      case "delete_permanent":
      case "stop":
        return "danger";
      case "block":
      case "delete_soft":
        return "warning";
      default:
        return "default";
    }
  };

  const formatAction = (action: string) => {
    return action.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const formatDate = (date: string) => {
    const d = new Date(date);
    return d.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Spinner size="lg" />
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="text-center text-foreground/60 py-8">
        Nenhum log de auditoria encontrado
      </div>
    );
  }

  return (
    <Table aria-label="Tabela de auditoria" className="max-h-96">
      <TableHeader>
        <TableColumn>Data/Hora</TableColumn>
        <TableColumn>Ação</TableColumn>
        <TableColumn>Ator</TableColumn>
        <TableColumn>Alvo</TableColumn>
        <TableColumn>Detalhes</TableColumn>
      </TableHeader>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log._id}>
            <TableCell>
              <div className="flex items-center gap-2 text-xs">
                <FontAwesomeIcon icon={faClock} className="text-foreground/50" />
                {formatDate(log.createdAt)}
              </div>
            </TableCell>
            <TableCell>
              <Chip
                size="sm"
                color={getActionColor(log.action)}
                variant="flat"
                startContent={<FontAwesomeIcon icon={getActionIcon(log.action)} className="text-xs" />}
              >
                {formatAction(log.action)}
              </Chip>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1 text-xs">
                <FontAwesomeIcon icon={faUser} className="text-foreground/50" />
                {log.actorId || "Sistema"}
              </div>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1 text-xs">
                <FontAwesomeIcon icon={faServer} className="text-foreground/50" />
                <span className="truncate max-w-[150px]" title={log.targetId}>
                  {log.targetId}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <div className="text-xs text-foreground/70">
                {log.metadata?.reason && (
                  <p>Razão: {log.metadata.reason}</p>
                )}
                {log.metadata?.appId && (
                  <p>App ID: {log.metadata.appId}</p>
                )}
                {log.metadata?.oldRam && log.metadata?.newRam && (
                  <p>RAM: {log.metadata.oldRam} → {log.metadata.newRam} MB</p>
                )}
                {log.metadata?.ip && (
                  <p>IP: {log.metadata.ip}</p>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
