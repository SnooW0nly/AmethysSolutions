const { MongoClient } = require('mongodb');
const fs = require('fs');
const path = require('path');
const archiver = require('archiver');
const AdmZip = require('adm-zip');
const axios = require('axios');
const FormData = require('form-data');
const readline = require('readline');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURAÇÕES
// ═══════════════════════════════════════════════════════════════════════════════

const MONGODB_URI = process.env.MONGODB_URI;
const MONGODB_URI_DEFAULT = process.env.MONGODB_URI_RESTORE || process.env.MONGODB_URI;
const WEBHOOK_DISCORD = process.env.WEBHOOK_DISCORD;
const TEMP_SEGUNDOS = parseInt(process.env.TEMP_SEGUNDOS) || 10800;
const BACKUP_DIR = path.join(__dirname, 'backups');
const DIAS_RETENCAO = 7;

// Criar pasta de backups se não existir
if (!fs.existsSync(BACKUP_DIR)) {
    fs.mkdirSync(BACKUP_DIR, { recursive: true });
}

// Interface para input do usuário
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function question(prompt) {
    return new Promise((resolve) => rl.question(prompt, resolve));
}

function clearScreen() {
    console.clear();
}

function printHeader() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║         VISION WALLET - MONGODB BACKUP SYSTEM              ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    console.log('');
}

function formatDate(date) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}-${pad(date.getMinutes())}-${pad(date.getSeconds())}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// FUNÇÕES DE BACKUP
// ═══════════════════════════════════════════════════════════════════════════════

async function createBackup() {
    const timestamp = formatDate(new Date());
    const backupName = `backup_${timestamp}`;
    const backupPath = path.join(BACKUP_DIR, backupName);
    const zipPath = path.join(BACKUP_DIR, `${backupName}.zip`);

    console.log(`\n${'─'.repeat(60)}`);
    console.log(`📦 [${new Date().toLocaleString('pt-BR')}] Iniciando backup...`);
    console.log(`${'─'.repeat(60)}`);

    let client;

    try {
        console.log('\n📡 Conectando ao MongoDB...');
        client = new MongoClient(MONGODB_URI);
        await client.connect();
        console.log('✅ Conectado com sucesso!');

        const dbName = MONGODB_URI.split('/').pop().split('?')[0] || 'production';
        const db = client.db(dbName);

        fs.mkdirSync(backupPath, { recursive: true });

        const collections = await db.listCollections().toArray();
        console.log(`\n📋 Encontradas ${collections.length} coleções\n`);

        for (const collInfo of collections) {
            const collName = collInfo.name;
            const collection = db.collection(collName);
            const documents = await collection.find({}).toArray();
            const filePath = path.join(backupPath, `${collName}.json`);
            fs.writeFileSync(filePath, JSON.stringify(documents, null, 2));
            console.log(`   ✓ ${collName}: ${documents.length} documentos`);
        }

        console.log('\n📦 Compactando backup...');
        await createZip(backupPath, zipPath);

        const stats = fs.statSync(zipPath);
        const fileSizeMB = (stats.size / (1024 * 1024)).toFixed(2);
        console.log(`✅ Backup compactado! (${fileSizeMB} MB)`);

        console.log('\n📤 Enviando para Discord...');
        await sendToDiscord(zipPath, backupName, fileSizeMB);
        console.log('✅ Enviado para Discord!');

        fs.rmSync(backupPath, { recursive: true, force: true });
        await cleanOldBackups();

        console.log(`\n${'─'.repeat(60)}`);
        console.log(`✅ BACKUP CONCLUÍDO COM SUCESSO!`);
        console.log(`📁 Arquivo: ${backupName}.zip`);
        console.log(`${'─'.repeat(60)}`);

        return { success: true, path: zipPath };

    } catch (error) {
        console.error('\n❌ Erro durante o backup:', error.message);

        if (fs.existsSync(backupPath)) fs.rmSync(backupPath, { recursive: true, force: true });
        if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);

        try {
            await axios.post(WEBHOOK_DISCORD, {
                content: `❌ **Erro no Backup MongoDB**\n\`\`\`${error.message}\`\`\`\n⏰ ${new Date().toLocaleString('pt-BR')}`
            });
        } catch (e) { }

        return { success: false, error: error.message };

    } finally {
        if (client) await client.close();
    }
}

function createZip(sourceDir, zipPath) {
    return new Promise((resolve, reject) => {
        const output = fs.createWriteStream(zipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });
        output.on('close', () => resolve());
        archive.on('error', (err) => reject(err));
        archive.pipe(output);
        archive.directory(sourceDir, false);
        archive.finalize();
    });
}

async function sendToDiscord(filePath, backupName, sizeMB) {
    const form = new FormData();
    const payload = {
        content: `🔒 **Backup MongoDB Automático**`,
        embeds: [{
            title: '✅ Backup Concluído',
            color: 0x00ff00,
            fields: [
                { name: '📁 Arquivo', value: `\`${backupName}.zip\``, inline: true },
                { name: '📊 Tamanho', value: `${sizeMB} MB`, inline: true },
                { name: '⏰ Data/Hora', value: new Date().toLocaleString('pt-BR'), inline: true }
            ],
            footer: { text: 'Amethys Wallet Backup System' },
            timestamp: new Date().toISOString()
        }]
    };

    form.append('payload_json', JSON.stringify(payload));
    form.append('file', fs.createReadStream(filePath), { filename: `${backupName}.zip` });

    await axios.post(WEBHOOK_DISCORD, form, {
        headers: form.getHeaders(),
        maxBodyLength: Infinity,
        maxContentLength: Infinity
    });
}

async function cleanOldBackups() {
    const files = fs.readdirSync(BACKUP_DIR);
    const now = Date.now();
    const maxAge = DIAS_RETENCAO * 24 * 60 * 60 * 1000;
    let removidos = 0;

    for (const file of files) {
        if (!file.endsWith('.zip')) continue;
        const filePath = path.join(BACKUP_DIR, file);
        const stats = fs.statSync(filePath);
        if (now - stats.mtimeMs > maxAge) {
            fs.unlinkSync(filePath);
            console.log(`   🗑️ Removido: ${file}`);
            removidos++;
        }
    }

    if (removidos > 0) console.log(`\n🧹 ${removidos} backup(s) antigo(s) removido(s)`);
}

// ═══════════════════════════════════════════════════════════════════════════════
// FUNÇÕES DE RESTORE
// ═══════════════════════════════════════════════════════════════════════════════

function listBackups() {
    if (!fs.existsSync(BACKUP_DIR)) return [];
    return fs.readdirSync(BACKUP_DIR).filter(f => f.endsWith('.zip')).sort().reverse();
}

async function restoreBackup(backupName, customUri = null) {
    const zipPath = path.join(BACKUP_DIR, backupName);
    const extractPath = path.join(BACKUP_DIR, '_restore_temp');

    if (!fs.existsSync(zipPath)) {
        console.error(`\n❌ Arquivo não encontrado: ${zipPath}`);
        return { success: false };
    }

    // Pedir URI ao usuário se não foi passada
    let restoreUri = customUri;
    if (!restoreUri) {
        console.log('\n📡 Informe a URI do MongoDB de destino:');
        console.log(`   (Pressione ENTER para usar: ${MONGODB_URI_DEFAULT ? MONGODB_URI_DEFAULT.substring(0, 50) + '...' : 'não configurada'})\n`);
        const inputUri = await question('URI: ');
        restoreUri = inputUri.trim() || MONGODB_URI_DEFAULT;
    }

    if (!restoreUri) {
        console.error('\n❌ Nenhuma URI informada e MONGODB_URI não configurada no .env');
        return { success: false };
    }

    let client;

    try {
        console.log('\n📦 Extraindo backup...');
        if (fs.existsSync(extractPath)) fs.rmSync(extractPath, { recursive: true, force: true });

        const zip = new AdmZip(zipPath);
        zip.extractAllTo(extractPath, true);
        console.log('✅ Backup extraído!');

        console.log('\n📡 Conectando ao MongoDB de destino...');

        client = new MongoClient(restoreUri);
        await client.connect();
        console.log('✅ Conectado com sucesso!');

        const dbName = restoreUri.split('/').pop().split('?')[0] || 'production';
        const db = client.db(dbName);
        console.log(`📁 Banco de dados: ${dbName}`);

        const jsonFiles = fs.readdirSync(extractPath).filter(f => f.endsWith('.json'));
        console.log(`\n📋 Encontradas ${jsonFiles.length} coleções\n`);

        console.log('⚠️  ATENÇÃO: Isso irá SUBSTITUIR os dados existentes!');
        const confirm = await question('   Deseja continuar? (s/N): ');

        if (confirm.toLowerCase() !== 's') {
            console.log('\n❌ Restauração cancelada.');
            return { success: false };
        }

        let totalDocs = 0;
        for (const file of jsonFiles) {
            const collName = path.basename(file, '.json');
            const filePath = path.join(extractPath, file);
            const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

            if (!Array.isArray(data) || data.length === 0) continue;

            const collection = db.collection(collName);
            await collection.deleteMany({});
            const result = await collection.insertMany(data);
            console.log(`   ✓ ${collName}: ${result.insertedCount} documentos`);
            totalDocs += result.insertedCount;
        }

        fs.rmSync(extractPath, { recursive: true, force: true });

        console.log(`\n${'─'.repeat(60)}`);
        console.log(`✅ RESTAURAÇÃO CONCLUÍDA!`);
        console.log(`📊 Total: ${totalDocs} documentos em ${jsonFiles.length} coleções`);
        console.log(`${'─'.repeat(60)}`);

        return { success: true };

    } catch (error) {
        console.error('\n❌ Erro durante a restauração:', error.message);
        if (fs.existsSync(extractPath)) fs.rmSync(extractPath, { recursive: true, force: true });
        return { success: false };

    } finally {
        if (client) await client.close();
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MENU INTERATIVO
// ═══════════════════════════════════════════════════════════════════════════════

async function menuBackup() {
    clearScreen();
    printHeader();
    console.log('📦 BACKUP MONGODB\n');
    console.log('   1. Backup manual (único)');
    console.log('   2. Backup automático (loop contínuo)');
    console.log('   0. Voltar\n');

    const choice = await question('Escolha uma opção: ');

    switch (choice) {
        case '1':
            await createBackup();
            await question('\nPressione ENTER para continuar...');
            break;
        case '2':
            console.log(`\n🔁 Modo automático iniciado!`);
            console.log(`   Intervalo: ${TEMP_SEGUNDOS} segundos (${(TEMP_SEGUNDOS / 3600).toFixed(1)} horas)`);
            console.log(`   Pressione Ctrl+C para parar\n`);
            await createBackup();
            await runAutoBackup();
            break;
        case '0':
            return;
        default:
            console.log('\n❌ Opção inválida!');
            await question('Pressione ENTER para continuar...');
    }
}

async function runAutoBackup() {
    return new Promise(() => {
        setInterval(async () => {
            await createBackup();
        }, TEMP_SEGUNDOS * 1000);
    });
}

async function menuRestore() {
    clearScreen();
    printHeader();
    console.log('🔄 RESTAURAR BACKUP\n');

    const backups = listBackups();

    if (backups.length === 0) {
        console.log('❌ Nenhum backup encontrado!\n');
        await question('Pressione ENTER para continuar...');
        return;
    }

    console.log('Backups disponíveis:\n');
    backups.forEach((backup, index) => {
        const stats = fs.statSync(path.join(BACKUP_DIR, backup));
        const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
        const date = new Date(stats.mtime).toLocaleString('pt-BR');
        console.log(`   ${index + 1}. ${backup}`);
        console.log(`      📊 ${sizeMB} MB | 📅 ${date}\n`);
    });

    console.log('   0. Voltar\n');

    const choice = await question('Digite o número do backup: ');

    if (choice === '0') return;

    const index = parseInt(choice) - 1;
    if (isNaN(index) || index < 0 || index >= backups.length) {
        console.log('\n❌ Opção inválida!');
        await question('Pressione ENTER para continuar...');
        return;
    }

    await restoreBackup(backups[index]);
    await question('\nPressione ENTER para continuar...');
}

async function menuConfig() {
    clearScreen();
    printHeader();
    console.log('⚙️  CONFIGURAÇÕES ATUAIS\n');
    console.log(`   📡 MONGODB_URI: ${MONGODB_URI ? '✅ Configurada' : '❌ Não configurada'}`);
    console.log(`   📤 WEBHOOK_DISCORD: ${WEBHOOK_DISCORD ? '✅ Configurado' : '❌ Não configurado'}`);
    console.log(`   ⏰ TEMP_SEGUNDOS: ${TEMP_SEGUNDOS} (${(TEMP_SEGUNDOS / 3600).toFixed(1)} horas)`);
    console.log(`   📁 BACKUP_DIR: ${BACKUP_DIR}`);
    console.log(`   🗑️  DIAS_RETENCAO: ${DIAS_RETENCAO} dias`);

    const backups = listBackups();
    console.log(`\n   📦 Backups salvos: ${backups.length}`);

    console.log('\n   Edite o arquivo .env para alterar as configurações.\n');
    await question('Pressione ENTER para continuar...');
}

async function menuPrincipal() {
    while (true) {
        clearScreen();
        printHeader();
        console.log('MENU PRINCIPAL\n');
        console.log('   1. 📦 Fazer Backup');
        console.log('   2. 🔄 Restaurar Backup');
        console.log('   3. ⚙️  Ver Configurações');
        console.log('   0. 🚪 Sair\n');

        const choice = await question('Escolha uma opção: ');

        switch (choice) {
            case '1':
                await menuBackup();
                break;
            case '2':
                await menuRestore();
                break;
            case '3':
                await menuConfig();
                break;
            case '0':
                clearScreen();
                console.log('\n👋 Até logo!\n');
                rl.close();
                process.exit(0);
            default:
                console.log('\n❌ Opção inválida!');
                await question('Pressione ENTER para continuar...');
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// EXECUÇÃO
// ═══════════════════════════════════════════════════════════════════════════════

async function main() {
    // Verificar argumentos de linha de comando
    const args = process.argv.slice(2);

    if (args.includes('--backup') || args.includes('-b')) {
        await createBackup();
        process.exit(0);
    }

    if (args.includes('--auto') || args.includes('-a')) {
        console.log(`\n🔁 Modo automático iniciado!`);
        console.log(`   Intervalo: ${TEMP_SEGUNDOS} segundos`);
        await createBackup();
        await runAutoBackup();
        return;
    }

    if (args.includes('--restore') || args.includes('-r')) {
        const backups = listBackups();
        if (backups.length > 0) {
            console.log('\nBackups disponíveis:');
            backups.forEach((b, i) => console.log(`   ${i + 1}. ${b}`));
            const choice = await question('\nDigite o número: ');
            const index = parseInt(choice) - 1;
            if (index >= 0 && index < backups.length) {
                await restoreBackup(backups[index]);
            }
        } else {
            console.log('\n❌ Nenhum backup encontrado!');
        }
        rl.close();
        process.exit(0);
    }

    // Modo interativo
    await menuPrincipal();
}

main().catch((err) => {
    console.error('Erro:', err);
    rl.close();
    process.exit(1);
});
