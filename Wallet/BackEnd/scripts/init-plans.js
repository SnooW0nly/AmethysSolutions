/**
 * Script para inicializar planos no MongoDB
 * 
 * Uso: node scripts/init-plans.js
 */

import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

// Configurar __dirname para ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carregar variáveis de ambiente
const backendEnvPath = path.join(__dirname, '..', '.env');
const rootEnvPath = path.join(__dirname, '..', '..', '.env');

if (existsSync(backendEnvPath)) {
  dotenv.config({ path: backendEnvPath });
  console.log(`[ENV] ✓ Carregado: ${backendEnvPath}`);
} else if (existsSync(rootEnvPath)) {
  dotenv.config({ path: rootEnvPath });
  console.log(`[ENV] ✓ Carregado: ${rootEnvPath}`);
} else {
  console.warn(`[ENV] ⚠ Nenhum arquivo .env encontrado`);
  dotenv.config();
}

// Importar modelo Plan
import Plan from '../src/database/models/Plan.js';

const defaultPlans = [
  {
    id: 'FREE',
    name: 'FREE',
    description: 'Ideal para começar',
    transactionFee: 70,
    monthlyFee: 0,
    minTransactions: 0,
    maxTransactions: 300,
    downgradeTo: null,
    order: 0,
    active: true,
  },
  {
    id: 'CARBON',
    name: 'CARBON',
    description: 'Para pequenos negócios',
    transactionFee: 65,
    monthlyFee: 1997,
    minTransactions: 300,
    maxTransactions: 800,
    downgradeTo: 'FREE',
    order: 1,
    active: true,
  },
  {
    id: 'DIAMOND',
    name: 'DIAMOND',
    description: 'Para empresas em crescimento',
    transactionFee: 60,
    monthlyFee: 4997,
    minTransactions: 800,
    maxTransactions: 2000,
    downgradeTo: 'CARBON',
    order: 2,
    active: true,
  },
  {
    id: 'RICH',
    name: 'RICH',
    description: 'Para grandes volumes',
    transactionFee: 55,
    monthlyFee: 14997,
    minTransactions: 3000,
    maxTransactions: 6000,
    downgradeTo: 'DIAMOND',
    order: 3,
    active: true,
  },
  {
    id: 'ENTERPRISE',
    name: 'ENTERPRISE',
    description: 'Solução corporativa',
    transactionFee: 50,
    monthlyFee: 99997,
    minTransactions: 6000,
    maxTransactions: null,
    downgradeTo: 'RICH',
    order: 4,
    active: true,
  },
];

async function initPlans() {
  try {
    const MONGODB_URI = process.env.MONGODB_URI;
    
    if (!MONGODB_URI) {
      console.error('❌ Erro: MONGODB_URI não está definido no .env');
      process.exit(1);
    }

    console.log('🔌 Conectando ao MongoDB...');
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Conectado ao MongoDB\n');

    let created = 0;
    let updated = 0;
    let skipped = 0;

    for (const planData of defaultPlans) {
      try {
        const existing = await Plan.findOne({ id: planData.id });
        
        if (existing) {
          // Atualizar plano existente
          await Plan.findOneAndUpdate(
            { id: planData.id },
            { $set: planData },
            { new: true }
          );
          updated++;
          console.log(`📝 Plano ${planData.id} atualizado`);
        } else {
          // Criar novo plano
          await Plan.create(planData);
          created++;
          console.log(`✅ Plano ${planData.id} criado`);
        }
      } catch (error) {
        console.error(`❌ Erro ao processar plano ${planData.id}:`, error.message);
        skipped++;
      }
    }

    console.log(`\n📊 Resumo:`);
    console.log(`   Criados: ${created}`);
    console.log(`   Atualizados: ${updated}`);
    console.log(`   Erros: ${skipped}`);

    // Listar todos os planos
    const allPlans = await Plan.find({ active: true }).sort({ order: 1 });
    console.log(`\n📋 Planos ativos (${allPlans.length}):`);
    allPlans.forEach(plan => {
      console.log(`   - ${plan.id}: ${plan.name} (Taxa: R$ ${(plan.transactionFee / 100).toFixed(2)}, Mensalidade: R$ ${(plan.monthlyFee / 100).toFixed(2)})`);
    });

    await mongoose.disconnect();
    console.log('\n🔌 Desconectado do MongoDB');
    process.exit(0);

  } catch (error) {
    console.error('❌ Erro ao inicializar planos:', error);
    await mongoose.disconnect();
    process.exit(1);
  }
}

initPlans();

