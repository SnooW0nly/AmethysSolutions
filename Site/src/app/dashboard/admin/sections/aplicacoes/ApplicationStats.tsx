"use client";

import { Card, CardBody } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faServer,
  faCheckCircle,
  faTimesCircle,
  faBan,
  faTrash,
  faChartPie,
  faClock,
  faExclamationTriangle,
} from "@fortawesome/free-solid-svg-icons";

interface ApplicationStatsProps {
  stats: {
    total: number;
    active: number;
    expired: number;
    blocked: number;
    deleted: number;
    byPlan: Record<string, number>;
    recentCreated: any[];
    recentExpired: any[];
  };
}

export function ApplicationStats({ stats }: ApplicationStatsProps) {
  const statsCards = [
    {
      label: "Total",
      value: stats.total,
      icon: faServer,
      color: "primary",
    },
    {
      label: "Ativas",
      value: stats.active,
      icon: faCheckCircle,
      color: "success",
    },
    {
      label: "Expiradas",
      value: stats.expired,
      icon: faTimesCircle,
      color: "danger",
    },
    {
      label: "Bloqueadas",
      value: stats.blocked,
      icon: faBan,
      color: "warning",
    },
    {
      label: "Deletadas",
      value: stats.deleted,
      icon: faTrash,
      color: "default",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Cards de estatísticas */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {statsCards.map((stat) => (
          <Card key={stat.label} className="border border-foreground/10">
            <CardBody className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-foreground/60">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
                <div className={`text-${stat.color} opacity-20`}>
                  <FontAwesomeIcon icon={stat.icon} className="text-2xl" />
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Estatísticas por plano */}
      {Object.keys(stats.byPlan).length > 0 && (
        <Card className="border border-foreground/10">
          <CardBody className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <FontAwesomeIcon icon={faChartPie} className="text-foreground/50" />
              <h4 className="font-semibold">Distribuição por Plano</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(stats.byPlan).map(([plan, count]) => (
                <div key={plan} className="text-center p-2 rounded-lg bg-foreground/5">
                  <p className="text-xs text-foreground/60">{plan}</p>
                  <p className="text-lg font-semibold">{count}</p>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Aplicações recentes */}
        {stats.recentCreated.length > 0 && (
          <Card className="border border-foreground/10">
            <CardBody className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <FontAwesomeIcon icon={faClock} className="text-foreground/50" />
                <h4 className="font-semibold text-sm">Criadas Recentemente</h4>
              </div>
              <div className="space-y-2">
                {stats.recentCreated.map((app) => (
                  <div key={app._id} className="flex justify-between items-center text-xs">
                    <div>
                      <p className="font-medium">{app.name}</p>
                      <p className="text-foreground/60">
                        {app.userId?.username || "Usuário"}
                      </p>
                    </div>
                    <p className="text-foreground/60">
                      {new Date(app.createdAt).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        )}

        {/* Aplicações prestes a expirar */}
        {stats.recentExpired.length > 0 && (
          <Card className="border border-foreground/10">
            <CardBody className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <FontAwesomeIcon icon={faExclamationTriangle} className="text-warning" />
                <h4 className="font-semibold text-sm">Expirando em Breve</h4>
              </div>
              <div className="space-y-2">
                {stats.recentExpired.map((app) => (
                  <div key={app._id} className="flex justify-between items-center text-xs">
                    <div>
                      <p className="font-medium">{app.name}</p>
                      <p className="text-foreground/60">
                        {app.userId?.username || "Usuário"}
                      </p>
                    </div>
                    <p className="text-warning text-xs">
                      {new Date(app.expiresAt).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        )}
      </div>
    </div>
  );
}
