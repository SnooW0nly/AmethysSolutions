/**
 * Serviço de Auditoria
 * Registra todas as ações administrativas no sistema
 */

import AuditLog from "../database/models/AuditLog.js";

class AuditService {
  /**
   * Registra uma ação no log de auditoria
   */
  async log(entity, action, actorId, targetId, metadata = {}) {
    try {
      const log = new AuditLog({
        entity,
        action,
        actorId: actorId || "system",
        targetId: targetId || "",
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
          ip: metadata.ip || null,
          userAgent: metadata.userAgent || null,
        },
      });

      await log.save();
      console.log(`[AUDIT] ${entity}:${action} by ${actorId} on ${targetId}`);
      return log;
    } catch (error) {
      console.error("[AUDIT] Erro ao registrar log:", error);
      // Não lança erro para não interromper a operação principal
      return null;
    }
  }

  /**
   * Busca logs de auditoria com filtros
   */
  async getLogs(filters = {}, pagination = {}) {
    try {
      const {
        entity,
        action,
        actorId,
        targetId,
        from,
        to,
      } = filters;

      const {
        page = 1,
        limit = 20,
        sort = "-createdAt",
      } = pagination;

      const query = {};

      if (entity) query.entity = entity;
      if (action) query.action = action;
      if (actorId) query.actorId = actorId;
      if (targetId) query.targetId = new RegExp(targetId, "i");

      if (from || to) {
        query.createdAt = {};
        if (from) query.createdAt.$gte = new Date(from);
        if (to) {
          const endDate = new Date(to);
          endDate.setHours(23, 59, 59, 999);
          query.createdAt.$lte = endDate;
        }
      }

      const skip = (page - 1) * limit;

      const [logs, total] = await Promise.all([
        AuditLog.find(query)
          .sort(sort)
          .skip(skip)
          .limit(limit)
          .lean(),
        AuditLog.countDocuments(query),
      ]);

      return {
        logs,
        total,
        page,
        limit,
        pages: Math.ceil(total / limit),
      };
    } catch (error) {
      console.error("[AUDIT] Erro ao buscar logs:", error);
      throw error;
    }
  }

  /**
   * Busca estatísticas de auditoria
   */
  async getStats(entity = null, days = 30) {
    try {
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);

      const match = {
        createdAt: { $gte: startDate },
      };

      if (entity) {
        match.entity = entity;
      }

      const stats = await AuditLog.aggregate([
        { $match: match },
        {
          $group: {
            _id: {
              entity: "$entity",
              action: "$action",
              date: {
                $dateToString: {
                  format: "%Y-%m-%d",
                  date: "$createdAt",
                },
              },
            },
            count: { $sum: 1 },
          },
        },
        {
          $group: {
            _id: {
              entity: "$_id.entity",
              action: "$_id.action",
            },
            total: { $sum: "$count" },
            dailyData: {
              $push: {
                date: "$_id.date",
                count: "$count",
              },
            },
          },
        },
        {
          $group: {
            _id: "$_id.entity",
            actions: {
              $push: {
                action: "$_id.action",
                total: "$total",
                dailyData: "$dailyData",
              },
            },
            totalActions: { $sum: "$total" },
          },
        },
        {
          $sort: { totalActions: -1 },
        },
      ]);

      return stats;
    } catch (error) {
      console.error("[AUDIT] Erro ao buscar estatísticas:", error);
      throw error;
    }
  }

  /**
   * Limpa logs antigos (manutenção)
   */
  async cleanOldLogs(daysToKeep = 90) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

      const result = await AuditLog.deleteMany({
        createdAt: { $lt: cutoffDate },
      });

      console.log(`[AUDIT] ${result.deletedCount} logs antigos removidos`);
      return result.deletedCount;
    } catch (error) {
      console.error("[AUDIT] Erro ao limpar logs antigos:", error);
      throw error;
    }
  }
}

export default new AuditService();
