import express from 'express';
import https from 'https';
import dotenv from 'dotenv';

dotenv.config();

const router = express.Router();

function fetchMisticTransactions(account = 'default', limit = 50) {
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

        const url = new URL(`${process.env.MISTIC_API_URL}/api/users/transactions`);
        url.searchParams.append('limit', limit);

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
                    resolve({
                        success: true,
                        data: json?.data || []
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
                error: 'Erro ao consultar transações na MisticPay'
            });
        });

        request.on('timeout', () => {
            request.destroy();
            resolve({
                success: false,
                error: 'Timeout ao consultar transações na MisticPay'
            });
        });

        request.end();
    });
}

router.get('/white', async (req, res) => {
    try {
        const result = await fetchMisticTransactions('default');

        if (!result.success) {
            return res.status(500).json({
                success: false,
                error: result.error
            });
        }

        return res.json({
            success: true,
            data: result.data
        });
    } catch (error) {
        console.error('Erro geral Mistic transactions/white:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

router.get('/black', async (req, res) => {
    try {
        const result = await fetchMisticTransactions('black');

        if (!result.success) {
            return res.status(500).json({
                success: false,
                error: result.error
            });
        }

        return res.json({
            success: true,
            data: result.data
        });
    } catch (error) {
        console.error('Erro geral Mistic transactions/black:', error);
        res.status(500).json({
            success: false,
            error: 'Erro interno do servidor',
            message: error.message
        });
    }
});

export default router;
