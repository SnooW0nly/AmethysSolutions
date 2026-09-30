/**
 * Script para definir um usuário como admin
 * 
 * Uso: node scripts/set-admin.js <userId>
 * Exemplo: node scripts/set-admin.js 692dff925b3d26812a0b9315
 */

import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

// Configurar __dirname para ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carregar variáveis de ambiente (tentar múltiplos caminhos)
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
  dotenv.config(); // Tentar carregar do diretório atual
}

// Importar modelo User
import User from '../src/database/models/User.js';

const userId = process.argv[2] || '692dff925b3d26812a0b9315';

async function setAdmin() {
  try {
    // Conectar ao MongoDB
    const MONGODB_URI = process.env.MONGODB_URI;
    
    if (!MONGODB_URI) {
      console.error('❌ Erro: MONGODB_URI não está definido no .env');
      process.exit(1);
    }

    console.log('🔌 Conectando ao MongoDB...');
    await mongoose.connect(MONGODB_URI);
    console.log('✅ Conectado ao MongoDB\n');

    // Buscar usuário
    console.log(`🔍 Buscando usuário com ID: ${userId}`);
    const user = await User.findById(userId);

    if (!user) {
      console.error(`❌ Usuário com ID ${userId} não encontrado`);
      await mongoose.disconnect();
      process.exit(1);
    }

    console.log(`📋 Usuário encontrado:`);
    console.log(`   Nome: ${user.fullName}`);
    console.log(`   Email: ${user.email}`);
    console.log(`   Admin atual: ${user.admin ? 'Sim' : 'Não'}\n`);

    // Verificar se já é admin
    if (user.admin) {
      console.log('⚠️  Usuário já é admin. Nenhuma alteração necessária.');
      await mongoose.disconnect();
      process.exit(0);
    }

    // Definir como admin
    console.log('🔧 Definindo usuário como admin...');
    user.admin = true;
    await user.save();

    console.log('✅ Usuário definido como admin com sucesso!');
    console.log(`\n📊 Informações atualizadas:`);
    console.log(`   Nome: ${user.fullName}`);
    console.log(`   Email: ${user.email}`);
    console.log(`   Admin: ${user.admin ? 'Sim' : 'Não'}`);
    console.log(`   Atualizado em: ${user.updatedAt}\n`);

    // Desconectar
    await mongoose.disconnect();
    console.log('🔌 Desconectado do MongoDB');
    process.exit(0);

  } catch (error) {
    console.error('❌ Erro ao definir usuário como admin:', error);
    await mongoose.disconnect();
    process.exit(1);
  }
}

// Executar script
setAdmin();

