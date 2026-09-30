import Register from '../database/models/Register.js';
import Payment from '../database/models/Payment.js';
import { getPlan, shouldUpgrade, shouldDowngrade, getNextPlan, calculatePlanConversion, initializePlanDates, getSplitFee, getPlanOrder } from './planService.js';
import Audit, { AUDIT_ACTIONS, AUDIT_ENTITIES } from '../database/models/Audit.js';
import { generateUniqueId } from './security.js';

/**
 * Analisa e atualiza planos dos usuários baseado nas transações mensais
 * Executa diariamente, mas apenas para usuários cuja renovação é amanhã (1 dia antes)
 */
export async function analyzeAndUpdatePlans() {
  try {
    console.log('🔍 Iniciando análise de planos (apenas usuários com renovação amanhã)...');
    
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    // Analisar mês anterior (fechamento mensal)
    const previousMonth = currentMonth === 1 ? 12 : currentMonth - 1;
    const previousYear = currentMonth === 1 ? currentYear - 1 : currentYear;
    
    // Buscar apenas usuários cuja renovação é amanhã (1 dia antes)
    const users = await Register.getUsersBeforeRenewal();
    let updated = 0;
    let upgraded = 0;
    let downgraded = 0;
    
    console.log(`📊 Encontrados ${users.length} usuário(s) com renovação amanhã para análise`);
    
    for (const user of users) {
      try {
        const currentPlan = user.plan || 'FREE';
        const autoUpgrade = user.autoUpgrade !== undefined ? user.autoUpgrade : false;
        
        // Contar transações do mês anterior
        const transactionCount = await Payment.countMonthlyTransactions(user.id, previousYear, previousMonth);
        
        // Verificar se precisa fazer upgrade
        const nextPlan = await shouldUpgrade(currentPlan, transactionCount);
        if (nextPlan && autoUpgrade) {
          const newPlan = await getPlan(nextPlan);
          const userBalance = user.balance || 0;
          
          if (newPlan.monthlyFee > 0 && userBalance < newPlan.monthlyFee) {
            console.log(`⚠️ Usuário ${user.id} (${user.name}) elegível para upgrade de ${currentPlan} para ${nextPlan}, mas saldo insuficiente`);
            await Register.findOneAndUpdate(
              { id: user.id },
              {
                $set: {
                  monthlyTransactions: transactionCount,
                  lastPlanCheck: now.toISOString()
                }
              }
            );
            updated++;
            continue;
          }
          
          const planEndDate = user.planEndDate || new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
          const conversion = await calculatePlanConversion(currentPlan, nextPlan, planEndDate);
          
          const requiredAmount = Math.max(0, newPlan.monthlyFee - conversion.creditAmount);
          
          if (requiredAmount > 0) {
            try {
              await Register.updateBalance(user.id, requiredAmount, 'subtract');
              console.log(`💳 Upgrade automático para ${nextPlan}: R$ ${(requiredAmount / 100).toFixed(2)} debitado`);
            } catch (balanceError) {
              console.error(`❌ Erro ao debitar mensalidade do usuário ${user.id}:`, balanceError.message);
            }
          }
          
          await Register.findOneAndUpdate(
            { id: user.id },
            {
              $set: {
                plan: nextPlan,
                paymentFee: newPlan.transactionFee,
                splitFee: await getSplitFee(nextPlan),
                planStartDate: now.toISOString(),
                planEndDate: conversion.newEndDate,
                planRenewalDate: conversion.planRenewalDate,
                monthlyTransactions: transactionCount,
                lastPlanCheck: now.toISOString(),
                planChangedAt: now.toISOString(),
                planChangeReason: 'UPGRADE_AUTOMATIC'
              }
            }
          );
          
          await Audit.saveLog({
            id: generateUniqueId(),
            action: AUDIT_ACTIONS.PLAN_UPGRADED,
            entity: AUDIT_ENTITIES.PLAN,
            entityId: user.id,
            userId: user.id,
            userEmail: user.email,
            dataBefore: {
              plan: currentPlan,
              paymentFee: user.paymentFee,
              splitFee: user.splitFee,
              planEndDate: user.planEndDate
            },
            dataAfter: {
              plan: nextPlan,
              paymentFee: newPlan.transactionFee,
              splitFee: await getSplitFee(nextPlan),
              planEndDate: conversion.newEndDate
            },
            metadata: {
              reason: 'UPGRADE_AUTOMATIC',
              transactionCount,
              requiredAmount,
              creditAmount: conversion.creditAmount,
              source: 'PLAN_ANALYZER'
            },
            description: `Upgrade automático de ${currentPlan} para ${nextPlan} - ${user.name} (${transactionCount} transações)`
          });
          
          upgraded++;
          console.log(`⬆️ Usuário ${user.id} (${user.name}) upgradeado de ${currentPlan} para ${nextPlan}`);
          continue;
        }
        
        // Verificar se precisa fazer downgrade
        const downgradePlan = await shouldDowngrade(currentPlan, transactionCount);
        if (downgradePlan) {
          const newPlan = await getPlan(downgradePlan);
          const newDates = initializePlanDates();
          
          await Register.findOneAndUpdate(
            { id: user.id },
            {
              $set: {
                plan: downgradePlan,
                paymentFee: newPlan.transactionFee,
                splitFee: await getSplitFee(downgradePlan),
                planStartDate: newDates.planStartDate,
                planEndDate: newDates.planEndDate,
                planRenewalDate: newDates.planRenewalDate,
                monthlyTransactions: transactionCount,
                lastPlanCheck: now.toISOString(),
                planChangedAt: now.toISOString(),
                planChangeReason: 'DOWNGRADE_AUTOMATIC'
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
              paymentFee: user.paymentFee,
              splitFee: user.splitFee
            },
            dataAfter: {
              plan: downgradePlan,
              paymentFee: newPlan.transactionFee,
              splitFee: await getSplitFee(downgradePlan)
            },
            metadata: {
              reason: 'DOWNGRADE_AUTOMATIC',
              transactionCount,
              minRequired: (await getPlan(currentPlan)).minTransactions,
              source: 'PLAN_ANALYZER'
            },
            description: `Downgrade automático de ${currentPlan} para ${downgradePlan} - ${user.name}`
          });
          
          downgraded++;
          console.log(`⬇️ Usuário ${user.id} (${user.name}) rebaixado de ${currentPlan} para ${downgradePlan}`);
          continue;
        }
        
        // Apenas atualizar contagem de transações
        await Register.findOneAndUpdate(
          { id: user.id },
          {
            $set: {
              monthlyTransactions: transactionCount,
              lastPlanCheck: now.toISOString()
            }
          }
        );
        updated++;
        
      } catch (userError) {
        console.error(`❌ Erro ao analisar plano do usuário ${user.id}:`, userError.message);
      }
    }
    
    console.log(`✅ Análise de planos concluída: ${upgraded} upgrade(s), ${downgraded} downgrade(s), ${updated} atualizado(s)`);
    
    await Audit.saveLog({
      id: generateUniqueId(),
      action: AUDIT_ACTIONS.PLAN_ANALYSIS_EXECUTED,
      entity: AUDIT_ENTITIES.SYSTEM,
      entityId: 'PLAN_ANALYZER',
      userId: 'SYSTEM',
      userEmail: null,
      metadata: {
        upgraded,
        downgraded,
        updated,
        total: users.length,
        previousMonth,
        previousYear
      },
      description: `Análise mensal de planos executada: ${upgraded} upgrade(s), ${downgraded} downgrade(s), ${updated} atualizado(s)`
    });
    
    return { upgraded, downgraded, updated, total: users.length };
    
  } catch (error) {
    console.error('❌ Erro na análise de planos:', error);
    return { upgraded: 0, downgraded: 0, updated: 0, total: 0 };
  }
}

/**
 * Verifica se um usuário específico deve fazer upgrade (para notificações)
 */
export async function checkUserUpgradeEligibility(userId) {
  try {
    const user = await Register.getById(userId);
    
    if (!user || user.status !== 'active' || user.blocked) {
      return null;
    }
    
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    const transactionCount = await Payment.countMonthlyTransactions(user.id, currentYear, currentMonth);
    const currentPlan = user.plan || 'FREE';
    
    const nextPlan = await shouldUpgrade(currentPlan, transactionCount);
    if (nextPlan) {
      const nextPlanConfig = await getPlan(nextPlan);
      return {
        eligible: true,
        currentPlan,
        nextPlan,
        currentTransactions: transactionCount,
        nextPlanFee: nextPlanConfig.transactionFee,
        nextPlanMonthlyFee: nextPlanConfig.monthlyFee,
        autoUpgradeEnabled: user.autoUpgrade || false
      };
    }
    
    return { eligible: false };
    
  } catch (error) {
    console.error(`❌ Erro ao verificar elegibilidade de upgrade do usuário ${userId}:`, error);
    return null;
  }
}

