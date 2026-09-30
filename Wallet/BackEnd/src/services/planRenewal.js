import Register from '../database/models/Register.js';
import { getPlan, renewPlanDates, getSplitFee } from './planService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../database/models/Audit.js';
import { generateUniqueId } from './security.js';

/**
 * Processa renovação de planos (executa 1 dia útil antes de vencer)
 */
export async function processPlanRenewals() {
  try {
    console.log('🔄 Verificando renovações de planos...');
    
    const usersToRenew = await Register.getUsersWithExpiringPlans();
    let renewed = 0;
    let failed = 0;
    
    for (const user of usersToRenew) {
      try {
        // Verificar se renovação automática está ativada
        const planAutoRenew = user.planAutoRenew !== undefined ? user.planAutoRenew : true;
        
        if (!planAutoRenew) {
          console.log(`⏭️ Renovação automática desativada para usuário ${user.id} (${user.name}) - pulando`);
          continue;
        }
        
        const currentPlan = user.plan || 'FREE';
        const planConfig = await getPlan(currentPlan);
        const userBalance = user.balance || 0;
        
        if (planConfig.monthlyFee > 0 && userBalance >= planConfig.monthlyFee) {
          // Debitar mensalidade
          await Register.updateBalance(user.id, planConfig.monthlyFee, 'subtract');
          
          const newDates = renewPlanDates();
          
          await Register.findOneAndUpdate(
            { id: user.id },
            {
              $set: {
                paymentFee: planConfig.transactionFee,
                splitFee: await getSplitFee(currentPlan),
                planStartDate: newDates.planStartDate,
                planEndDate: newDates.planEndDate,
                planRenewalDate: newDates.planRenewalDate,
                planChangedAt: new Date().toISOString(),
                planChangeReason: 'RENEWAL_AUTOMATIC'
              }
            }
          );
          
          await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.PLAN_RENEWED,
            entity: AUDIT_ENTITIES.PLAN,
            entityId: user.id,
            userId: user.id,
            userEmail: user.email,
            dataBefore: {
              planEndDate: user.planEndDate,
              planRenewalDate: user.planRenewalDate,
              balance: userBalance
            },
            dataAfter: {
              planEndDate: newDates.planEndDate,
              planRenewalDate: newDates.planRenewalDate,
              monthlyFee: planConfig.monthlyFee
            },
            metadata: {
              reason: 'RENEWAL_AUTOMATIC',
              source: 'PLAN_RENEWAL_SCHEDULER'
            },
            description: `Plano renovado automaticamente: ${currentPlan} - ${user.name}`
          });
          
          renewed++;
          console.log(`✅ Plano renovado para usuário ${user.id} (${user.name}) - Plano: ${currentPlan}`);
        } else {
          // Saldo insuficiente - não renova, volta para FREE
          const freePlan = await getPlan('FREE');
          const newDates = renewPlanDates();
          
          await Register.findOneAndUpdate(
            { id: user.id },
            {
              $set: {
                plan: 'FREE',
                paymentFee: freePlan.transactionFee,
                splitFee: await getSplitFee('FREE'),
                planStartDate: newDates.planStartDate,
                planEndDate: newDates.planEndDate,
                planRenewalDate: newDates.planRenewalDate,
                planChangedAt: new Date().toISOString(),
                planChangeReason: 'RENEWAL_FAILED_INSUFFICIENT_BALANCE'
              }
            }
          );
          
          await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.PLAN_DOWNGRADED,
            entity: AUDIT_ENTITIES.PLAN,
            entityId: user.id,
            userId: user.id,
            userEmail: user.email,
            dataBefore: {
              plan: currentPlan,
              balance: userBalance,
              requiredFee: planConfig.monthlyFee
            },
            dataAfter: {
              plan: 'FREE',
              paymentFee: freePlan.transactionFee
            },
            metadata: {
              reason: 'RENEWAL_FAILED_INSUFFICIENT_BALANCE',
              source: 'PLAN_RENEWAL_SCHEDULER'
            },
            description: `Renovação falhou - saldo insuficiente. Rebaixado para FREE: ${user.name}`
          });
          
          failed++;
          console.log(`⚠️ Renovação falhou para usuário ${user.id} (${user.name}) - Saldo insuficiente. Rebaixado para FREE.`);
        }
      } catch (error) {
        failed++;
        console.error(`❌ Erro ao renovar plano do usuário ${user.id}:`, error.message);
      }
    }
    
    console.log(`✅ Processamento de renovações concluído: ${renewed} renovado(s), ${failed} falha(s)`);
    
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_RENEWAL_EXECUTED,
      entity: AUDIT_ENTITIES.SYSTEM,
      entityId: 'PLAN_RENEWAL',
      userId: 'SYSTEM',
      userEmail: null,
      metadata: {
        renewed,
        failed,
        total: usersToRenew.length
      },
      description: `Processamento de renovações executado: ${renewed} renovado(s), ${failed} falha(s)`
    });
    
    return { renewed, failed, total: usersToRenew.length };
    
  } catch (error) {
    if (error.message && error.message.includes('MongoDB')) {
      console.warn('⚠️ Processamento de renovações: problema de conexão com MongoDB');
    } else {
      console.error('❌ Erro no processamento de renovações:', error.message || error);
    }
    return { renewed: 0, failed: 0, total: 0 };
  }
}

/**
 * Processa planos vencidos (rebaixa para FREE se não renovou)
 */
export async function processExpiredPlans() {
  try {
    console.log('⏰ Verificando planos vencidos...');
    
    const expiredUsers = await Register.getUsersWithExpiredPlans();
    let downgraded = 0;
    
    for (const user of expiredUsers) {
      try {
        const freePlan = await getPlan('FREE');
        const newDates = renewPlanDates();
        
        await Register.findOneAndUpdate(
          { id: user.id },
          {
            $set: {
              plan: 'FREE',
              paymentFee: freePlan.transactionFee,
              splitFee: getSplitFee('FREE'),
              planStartDate: newDates.planStartDate,
              planEndDate: newDates.planEndDate,
              planRenewalDate: newDates.planRenewalDate,
              planChangedAt: new Date().toISOString(),
              planChangeReason: 'EXPIRED_DOWNGRADE_TO_FREE'
            }
          }
        );
        
        await Audit.saveLog({
          id: generateUniqueId(),
          action: AUDIT_ACTIONS.PLAN_EXPIRED,
          entity: AUDIT_ENTITIES.PLAN,
          entityId: user.id,
          userId: user.id,
          userEmail: user.email,
          dataBefore: {
            plan: user.plan,
            planEndDate: user.planEndDate
          },
          dataAfter: {
            plan: 'FREE',
            paymentFee: freePlan.transactionFee
          },
          metadata: {
            reason: 'EXPIRED_DOWNGRADE_TO_FREE',
            source: 'PLAN_RENEWAL_SCHEDULER'
          },
          description: `Plano vencido - rebaixado para FREE: ${user.name}`
        });
        
        downgraded++;
        console.log(`⬇️ Usuário ${user.id} (${user.name}) rebaixado para FREE (plano vencido)`);
      } catch (error) {
        console.error(`❌ Erro ao processar plano vencido do usuário ${user.id}:`, error.message);
      }
    }
    
    console.log(`✅ Processamento de planos vencidos concluído: ${downgraded} rebaixado(s)`);
    
    if (downgraded > 0) {
      await Audit.saveLog({
        id: generateUniqueId(),
        action: AUDIT_ACTIONS.PLAN_EXPIRED,
        entity: AUDIT_ENTITIES.SYSTEM,
        entityId: 'EXPIRED_PLANS',
        userId: 'SYSTEM',
        userEmail: null,
        metadata: {
          downgraded,
          total: expiredUsers.length
        },
        description: `Processamento de planos vencidos executado: ${downgraded} rebaixado(s)`
      });
    }
    
    return { downgraded, total: expiredUsers.length };
    
  } catch (error) {
    if (error.message && error.message.includes('MongoDB')) {
      console.warn('⚠️ Processamento de planos vencidos: problema de conexão com MongoDB');
    } else {
      console.error('❌ Erro no processamento de planos vencidos:', error.message || error);
    }
    return { downgraded: 0, total: 0 };
  }
}

/**
 * Inicia o scheduler de renovação de planos
 * Verifica a cada hora se há planos para renovar
 */
export function startPlanRenewalScheduler() {
  console.log('📅 Iniciando scheduler de renovação de planos...');
  console.log('   - Verificação: a cada hora');
  console.log('   - Renovação: 1 dia útil antes do vencimento');
  console.log('   - Rebaixamento: automático quando vence sem renovação');
  
  // Executar imediatamente
  processPlanRenewals();
  processExpiredPlans();
  
  // Executar a cada hora
  setInterval(async () => {
    await processPlanRenewals();
    await processExpiredPlans();
  }, 60 * 60 * 1000); // 1 hora
}

