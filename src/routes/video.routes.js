'use strict';

const { Router } = require('express');
const { body } = require('express-validator');
const { uploadVideoMiddleware } = require('../middlewares/upload.middleware');
const videoController = require('../controllers/video.controller');

const router = Router();

/**
 * Validaciones de campos de texto.
 * Multer debe ejecutarse ANTES de express-validator para que req.body
 * esté disponible en los validadores.
 */
const validateAnalyzeRequest = [
  body('name')
    .trim()
    .notEmpty()
    .withMessage('El campo "name" es obligatorio.')
    .isLength({ max: 255 })
    .withMessage('El campo "name" no puede superar los 255 caracteres.'),

  body('galponId')
    .trim()
    .notEmpty()
    .withMessage('El campo "galponId" es obligatorio.')
    .isUUID(4)
    .withMessage('El campo "galponId" debe ser un UUID v4 válido.'),
];

/**
 * POST /api/videos/analyze
 *
 * Flujo de middlewares:
 *  1. uploadVideoMiddleware  → guarda el video en /tmp y valida formato/tamaño
 *  2. validateAnalyzeRequest → valida campos de texto
 *  3. videoController.analyze → procesa y responde
 */
router.post(
  '/analyze',
  uploadVideoMiddleware,
  validateAnalyzeRequest,
  (req, res, next) => videoController.analyze(req, res, next)
);

module.exports = router;
