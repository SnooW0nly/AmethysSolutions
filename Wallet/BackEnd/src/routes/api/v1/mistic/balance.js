import express from 'express';
import https from 'https';
import dotenv from 'dotenv';

dotenv.config();

const router = express.Router();

function fetchMisticBalance(account = 'default', type = 'all') {
    return new Promise((resolve) => {
        let ci, cs;

        if (account === 'black') {
            ci = process.env.MISTIC_BLACK_CLIENT;
            cs = process.env.MISTIC_BLACK_SECRET;
        } else {
            ci = process.env.MISTIC_CLIENT;
            cs = process.env.MISTIC_SECRET;
        }

        if (!ci || !cs) {
            return resolve({
                success: false,
                error: 'Credenciais da MisticPay não configuradas'
            });
        }

        const url = new URL(`${process.env.MISTIC_API_URL}/api/users/balance`);
        url.searchParams.append('type', type);

        const options = {
            method: 'GET',
            headers: { ci, cs },
            timeout: 10000
        };

        const request = https.request(url, options, (response) => {
            let body = '';

            response.on('data', chunk => {
                body += chunk;
            });

            response.on('end', () => {
                try {
                    const json = JSON.parse(body);
                    const balance = json?.data?.balance ?? 0;

                    resolve({
                        success: true,
                        balance,
                        formatted: balance.toLocaleString('pt-BR', {
                            style: 'currency',
                            currency: 'BRL'
                        })
                    });
                } catch (parseError) {
                    console.error('Erro ao parsear resposta da Mistic:', body);
                    resolve({
                        success: false,
                        error: 'Resposta inválida da MisticPay'
                    });
                }
            });
        });

        request.on('error', (err) => {
            console.error('Erro HTTPS MisticPay:', err.message);
            resolve({
                success: false,
                error: 'Erro ao consultar saldo na MisticPay'
            });
        });

        request.on('timeout', () => {
            request.destroy();
            resolve({
                success: false,
                error: 'Timeout ao consultar saldo na MisticPay'
            });
        });

        request.end();
    });
}

/**
 * GET /api/v1/mistic/balance/all
 * Returns combined total of white and black balances
 */
router.get('/all', async (req, res) => {
    try {
        const type = req.query.type || 'all';

        const [whiteResult, blackResult] = await Promise.all([
            fetchMisticBalance('default', type),
            fetchMisticBalance('black', type)
        ]);

        const whiteBalance = whiteResult.success ? whiteResult.balance : 0;
        const blackBalance = blackResult.success ? blackResult.balance : 0;
        const totalBalance = whiteBalance + blackBalance;

        return res.json({
            success: true,
            data: {
                type,
                white: {
                    balance: whiteBalance,
                    formatted: whiteBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
                },
                black: {
                    balance: blackBalance,
                    formatted: blackBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
                },
                total: {
                    balance: totalBalance,
                    formatted: totalBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
                }
            }
        });
    } catch (error) {
        console.error('Erro geral Mistic balance/all:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

/**
 * GET /api/v1/mistic/balance/white
 * Returns white (default) account balance
 */
router.get('/white', async (req, res) => {
    try {
        const type = req.query.type || 'all';
        const result = await fetchMisticBalance('default', type);

        if (!result.success) {
            return res.status(500).json({
                success: false,
                error: result.error
            });
        }

        return res.json({
            success: true,
            data: {
                account: 'white',
                type,
                balance: result.balance,
                formatted: result.formatted
            }
        });
    } catch (error) {
        console.error('Erro geral Mistic balance/white:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

/**
 * GET /api/v1/mistic/balance/black
 * Returns black account balance
 */
router.get('/black', async (req, res) => {
    try {
        const type = req.query.type || 'all';
        const result = await fetchMisticBalance('black', type);

        if (!result.success) {
            return res.status(500).json({
                success: false,
                error: result.error
            });
        }

        return res.json({
            success: true,
            data: {
                account: 'black',
                type,
                balance: result.balance,
                formatted: result.formatted
            }
        });
    } catch (error) {
        console.error('Erro geral Mistic balance/black:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;
