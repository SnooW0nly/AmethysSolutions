import express from 'express';
import Affiliate from '../../../../database/models/Affiliate.js';

const router = express.Router();

// GET /api/v1/affiliate/validate/:code - Validar código de afiliado (pública)
router.get('/:code', async (req, res) => {
    try {
        const { code } = req.params;

        if (!code || code.length < 3) {
            return res.status(400).json({
                valid: false,
                error: 'Código inválido'
            });
        }

        const affiliate = await Affiliate.getByCode(code);

        if (!affiliate) {
            return res.status(404).json({
                valid: false,
                error: 'Código não encontrado'
            });
        }

        res.json({
            valid: true,
            data: {
                code: affiliate.code,
                name: affiliate.userName ? affiliate.userName.split(' ')[0] : 'Afiliado'
            }
        });

    } catch (error) {
        console.error('[AFFILIATE] Erro ao validar código:', error.message);
        res.status(500).json({
            valid: false,
            error: 'Erro interno do servidor'
        });
    }
});

export default router;
