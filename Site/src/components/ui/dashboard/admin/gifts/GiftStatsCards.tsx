"use client";

import { GiftStatsResponse } from "@/types/gifts";
import { Gift, CheckCircle, XCircle, Clock } from "lucide-react";

interface GiftStatsCardsProps {
  stats: GiftStatsResponse;
}

export default function GiftStatsCards({ stats }: GiftStatsCardsProps) {
  const cards = [
    {
      title: "Total de Gifts",
      value: stats.general.total,
      icon: Gift,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      title: "Disponíveis",
      value: stats.general.available,
      icon: CheckCircle,
      color: "text-green-500",
      bgColor: "bg-green-500/10",
    },
    {
      title: "Usados",
      value: stats.general.used,
      icon: CheckCircle,
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
    {
      title: "Expirados",
      value: stats.general.expired,
      icon: Clock,
      color: "text-red-500",
      bgColor: "bg-red-500/10",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => (
        <div
          key={index}
          className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-6 hover:border-primary/50 transition-all hover:shadow-lg"
        >
          <div className="flex items-center justify-between mb-4">
            <div className={`p-3 ${card.bgColor} rounded-xl`}>
              <card.icon className={`w-6 h-6 ${card.color}`} />
            </div>
          </div>
          <div>
            <p className="text-sm text-foreground/60 mb-1 font-medium">{card.title}</p>
            <p className="text-3xl font-bold">{card.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
