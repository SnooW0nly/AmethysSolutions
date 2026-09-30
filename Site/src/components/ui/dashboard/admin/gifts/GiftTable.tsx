"use client";

import { Gift } from "@/types/gifts";
import { Copy, Trash2, CheckCircle, XCircle, Clock, Users } from "lucide-react";
import { useState } from "react";

interface GiftTableProps {
  gifts: Gift[];
  loading: boolean;
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  onPageChange: (page: number) => void;
  onDelete: (id: string) => void;
  onDeleteBatch: (batchId: string) => void;
}

export default function GiftTable({
  gifts,
  loading,
  pagination,
  onPageChange,
  onDelete,
  onDeleteBatch,
}: GiftTableProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const copyToClipboard = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const getStatusBadge = (gift: Gift) => {
    if (gift.isUsed) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-500/10 text-purple-500 rounded text-xs">
          <CheckCircle className="w-3 h-3" />
          Usado
        </span>
      );
    }

    if (gift.expiresAt && new Date(gift.expiresAt) < new Date()) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-500/10 text-red-500 rounded text-xs">
          <Clock className="w-3 h-3" />
          Expirado
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-500 rounded text-xs">
        <CheckCircle className="w-3 h-3" />
        Disponível
      </span>
    );
  };

  if (loading) {
    return (
      <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (gifts.length === 0) {
    return (
      <div className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl p-8">
        <div className="text-center text-foreground/60">
          <p>Nenhum gift encontrado</p>
        </div>
      </div>
    );
  }

  // Agrupa gifts por batchId
  const batchGroups = gifts.reduce((acc, gift) => {
    const key = gift.batchId || "individual";
    if (!acc[key]) acc[key] = [];
    acc[key].push(gift);
    return acc;
  }, {} as Record<string, Gift[]>);

  return (
    <div className="space-y-4">
      {Object.entries(batchGroups).map(([batchId, batchGifts]) => (
        <div key={batchId} className="bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl overflow-hidden">
          {/* Batch Header */}
          {batchId !== "individual" && (
            <div className="bg-foreground/5 px-4 py-3 border-b border-foreground/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Users className="w-4 h-4 text-foreground/60" />
                <div>
                  <p className="text-sm font-medium">Lote: {batchId}</p>
                  <p className="text-xs text-foreground/60">
                    {batchGifts.length} gift(s) • {batchGifts[0].planName} •{" "}
                    {[batchGifts[0].months ? `${batchGifts[0].months} mês(es)` : "", batchGifts[0].days ? `${batchGifts[0].days} dia(s)` : ""].filter(Boolean).join(" + ")}
                  </p>
                </div>
              </div>
              <button
                onClick={() => onDeleteBatch(batchId)}
                className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-xl text-sm flex items-center gap-2 transition-all font-medium"
              >
                <Trash2 className="w-3 h-3" />
                Deletar Lote
              </button>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-foreground/5">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Código
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Plano
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Duração
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Usado Por
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Criado Em
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-foreground/60 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-foreground/10">
                {batchGifts.map((gift) => (
                  <tr key={gift._id} className="hover:bg-foreground/5 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-mono bg-foreground/10 px-2 py-1 rounded-lg">
                          {gift.code}
                        </code>
                        <button
                          onClick={() => copyToClipboard(gift.code)}
                          className="p-1 hover:bg-foreground/10 rounded-lg transition-all"
                          title="Copiar código"
                        >
                          {copiedCode === gift.code ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4 text-foreground/40" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">{gift.planName}</td>
                    <td className="px-4 py-3 text-sm">
                      {[gift.months ? `${gift.months} mês(es)` : "", gift.days ? `${gift.days} dia(s)` : ""].filter(Boolean).join(" + ") || "—"}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(gift)}</td>
                    <td className="px-4 py-3 text-sm">
                      {gift.usedBy ? (
                        <div>
                          <p className="font-medium">{gift.usedBy.globalName}</p>
                          <p className="text-xs text-foreground/60">
                            {new Date(gift.usedAt!).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-foreground/40 font-mono">{gift.usedBy._id}</p>
                        </div>
                      ) : (
                        <span className="text-foreground/60">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground/60">
                      {new Date(gift.createdAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {!gift.isUsed && (
                        <button
                          onClick={() => onDelete(gift._id)}
                          className="p-2 hover:bg-red-500/10 text-red-500 rounded-lg transition-all"
                          title="Deletar gift"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Paginação */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-between bg-background/50 backdrop-blur-xl border border-foreground/10 rounded-xl px-4 py-3">
          <p className="text-sm text-foreground/60">
            Mostrando {((pagination.page - 1) * pagination.limit) + 1} a{" "}
            {Math.min(pagination.page * pagination.limit, pagination.total)} de{" "}
            {pagination.total} gifts
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
              className="px-3 py-1.5 bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all font-medium"
            >
              Anterior
            </button>
            <button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.pages}
              className="px-3 py-1.5 bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all font-medium"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
