/**
 * Sistema de cache para requisições à Discloud
 * Reduz requisições armazenando dados por 1 minuto
 */

class DiscloudCache {
  constructor() {
    this.cache = new Map();
    this.restartingApps = new Map(); // Armazena apps em estado de restart
    this.CACHE_TTL = 60 * 1000; // 1 minuto em milissegundos
    this.RESTARTING_TTL = 30 * 1000; // 30 segundos para status "restarting"
  }

  /**
   * Gera chave única para o cache
   */
  _getCacheKey(appId) {
    return `discloud_info_${appId}`;
  }

  /**
   * Verifica se o cache está válido
   */
  _isValid(entry) {
    if (!entry) return false;
    const now = Date.now();
    return (now - entry.timestamp) < this.CACHE_TTL;
  }

  /**
   * Obtém dados do cache se válidos
   * Se app estiver reiniciando, retorna status modificado
   */
  get(appId) {
    // Verifica se app está reiniciando
    const restartEntry = this.restartingApps.get(appId);
    if (restartEntry && (Date.now() - restartEntry.timestamp) < this.RESTARTING_TTL) {
      console.log(`[DiscloudCache] App ${appId} está REINICIANDO`);
      
      // Busca dados do cache normal
      const key = this._getCacheKey(appId);
      const entry = this.cache.get(key);
      
      if (entry && this._isValid(entry)) {
        // Retorna dados com status modificado para "restarting"
        const modifiedData = JSON.parse(JSON.stringify(entry.data));
        if (modifiedData.status) {
          modifiedData.status.container = "restarting";
        }
        return modifiedData;
      }
    }
    
    const key = this._getCacheKey(appId);
    const entry = this.cache.get(key);
    
    if (this._isValid(entry)) {
      console.log(`[DiscloudCache] Cache HIT para app ${appId}`);
      return entry.data;
    }
    
    console.log(`[DiscloudCache] Cache MISS para app ${appId}`);
    return null;
  }

  /**
   * Armazena dados no cache
   */
  set(appId, data) {
    const key = this._getCacheKey(appId);
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
    console.log(`[DiscloudCache] Dados armazenados para app ${appId}`);
  }

  /**
   * Remove entrada específica do cache
   */
  invalidate(appId) {
    const key = this._getCacheKey(appId);
    this.cache.delete(key);
    console.log(`[DiscloudCache] Cache invalidado para app ${appId}`);
  }

  /**
   * Limpa todo o cache
   */
  clear() {
    this.cache.clear();
    console.log(`[DiscloudCache] Cache completamente limpo`);
  }

  /**
   * Remove entradas expiradas (limpeza automática)
   */
  cleanup() {
    const now = Date.now();
    let removed = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if ((now - entry.timestamp) >= this.CACHE_TTL) {
        this.cache.delete(key);
        removed++;
      }
    }
    
    if (removed > 0) {
      console.log(`[DiscloudCache] Limpeza: ${removed} entradas removidas`);
    }
  }

  /**
   * Marca app como reiniciando
   */
  markAsRestarting(appId) {
    this.restartingApps.set(appId, {
      timestamp: Date.now()
    });
    console.log(`[DiscloudCache] App ${appId} marcado como REINICIANDO`);
    
    // Remove automaticamente após TTL
    setTimeout(() => {
      this.restartingApps.delete(appId);
      console.log(`[DiscloudCache] App ${appId} removido do estado REINICIANDO`);
    }, this.RESTARTING_TTL);
  }

  /**
   * Retorna estatísticas do cache
   */
  getStats() {
    return {
      size: this.cache.size,
      ttl: this.CACHE_TTL,
      entries: Array.from(this.cache.keys()),
      restartingApps: Array.from(this.restartingApps.keys())
    };
  }
}

// Instância singleton
const discloudCache = new DiscloudCache();

// Limpeza automática a cada 2 minutos
setInterval(() => {
  discloudCache.cleanup();
}, 2 * 60 * 1000);

export default discloudCache;
