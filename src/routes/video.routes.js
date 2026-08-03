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
 * @openapi
 * /api/videos/analyze:
 *   post:
 *     summary: Enviar un video para análisis en segundo plano
 *     tags:
 *       - Videos
 *     requestBody:
 *       required: true
 *       content:
 *         multipart/form-data:
 *           schema:
 *             type: object
 *             required:
 *               - file
 *               - name
 *               - galponId
 *             properties:
 *               file:
 *                 type: string
 *                 format: binary
 *                 description: Archivo de video (mp4, avi, mov, mkv)
 *               name:
 *                 type: string
 *                 example: Cinta Galpón A
 *                 description: Nombre descriptivo del análisis
 *               galponId:
 *                 type: string
 *                 format: uuid
 *                 example: a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d
 *                 description: UUID v4 del galpón
 *     responses:
 *       200:
 *         description: Video recibido correctamente, análisis iniciado en background
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 message:
 *                   type: string
 *                   example: Video recibido. El análisis está en proceso.
 *       400:
 *         description: Error de validación en los campos o archivo no proporcionado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ErrorResponse'
 */
router.post(
  '/analyze',
  uploadVideoMiddleware,
  validateAnalyzeRequest,
  (req, res, next) => videoController.analyze(req, res, next)
);

module.exports = router;
