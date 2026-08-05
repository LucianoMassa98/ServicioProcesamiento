'use strict';

const { Router } = require('express');
const { body, query } = require('express-validator');
const { uploadVideoMiddleware } = require('../middlewares/upload.middleware');
const videoController = require('../controllers/video.controller');

const router = Router();

/**
 * Validaciones para POST /api/videos/analyze
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
 * Validaciones para filtros por query string.
 */
const validateQueryFilters = [
  query('galponId')
    .optional()
    .trim()
    .isUUID(4)
    .withMessage('El parámetro "galponId" debe ser un UUID v4 válido.'),

  query('date')
    .optional()
    .trim()
    .isDate({ format: 'YYYY-MM-DD', strictMode: true })
    .withMessage('El parámetro "date" debe tener formato YYYY-MM-DD.'),

  query('startDate')
    .optional()
    .trim()
    .isDate({ format: 'YYYY-MM-DD', strictMode: true })
    .withMessage('El parámetro "startDate" debe tener formato YYYY-MM-DD.'),

  query('endDate')
    .optional()
    .trim()
    .isDate({ format: 'YYYY-MM-DD', strictMode: true })
    .withMessage('El parámetro "endDate" debe tener formato YYYY-MM-DD.'),

  query('limit')
    .optional()
    .isInt({ min: 1, max: 500 })
    .withMessage('El parámetro "limit" debe ser un entero entre 1 y 500.'),

  query('offset')
    .optional()
    .isInt({ min: 0 })
    .withMessage('El parámetro "offset" debe ser un entero mayor o igual a 0.'),
];

/**
 * @swagger
 * /api/videos/analyze:
 *   post:
 *     summary: Carga y analiza un video de cinta transportadora de huevos.
 *     tags: [Videos]
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
 *                 description: Archivo de video (mp4, avi, mov, mkv, webm).
 *               name:
 *                 type: string
 *                 description: Nombre descriptivo del análisis.
 *               galponId:
 *                 type: string
 *                 format: uuid
 *                 description: Identificador único del galpón.
 *     responses:
 *       200:
 *         description: Video recibido y en proceso de análisis en background.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ApiResponse'
 *       400:
 *         description: Error en datos de entrada o archivo inválido.
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

/**
 * @swagger
 * /api/videos/consolidated:
 *   get:
 *     summary: Obtiene información consolidada por día y por galpón (cantidad total de huevos contados).
 *     tags: [Videos]
 *     parameters:
 *       - in: query
 *         name: galponId
 *         schema:
 *           type: string
 *           format: uuid
 *         description: Filtrar por ID de galpón.
 *       - in: query
 *         name: date
 *         schema:
 *           type: string
 *           format: date
 *         description: Filtrar por un día específico (YYYY-MM-DD).
 *       - in: query
 *         name: startDate
 *         schema:
 *           type: string
 *           format: date
 *         description: Fecha de inicio para un lapso de tiempo (YYYY-MM-DD).
 *       - in: query
 *         name: endDate
 *         schema:
 *           type: string
 *           format: date
 *         description: Fecha de fin para un lapso de tiempo (YYYY-MM-DD).
 *     responses:
 *       200:
 *         description: Consolidado diario obtenido exitosamente.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 data:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/ConsolidatedDay'
 *       400:
 *         description: Parámetros de búsqueda inválidos.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ErrorResponse'
 */
router.get(
  '/consolidated',
  validateQueryFilters,
  (req, res, next) => videoController.getConsolidated(req, res, next)
);

/**
 * @swagger
 * /api/videos/records:
 *   get:
 *     summary: Obtiene los registros de archivos procesados con la cantidad de huevos contados.
 *     description: Devuelve la lista en formato de array [archivo, cnthuevos, createdAt, updatedAt] u objetos.
 *     tags: [Videos]
 *     parameters:
 *       - in: query
 *         name: galponId
 *         schema:
 *           type: string
 *           format: uuid
 *         description: Filtrar por ID de galpón.
 *       - in: query
 *         name: date
 *         schema:
 *           type: string
 *           format: date
 *         description: Filtrar por un día específico (YYYY-MM-DD).
 *       - in: query
 *         name: startDate
 *         schema:
 *           type: string
 *           format: date
 *         description: Fecha de inicio para lapso de tiempo (YYYY-MM-DD).
 *       - in: query
 *         name: endDate
 *         schema:
 *           type: string
 *           format: date
 *         description: Fecha de fin para lapso de tiempo (YYYY-MM-DD).
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 50
 *         description: Límite de resultados para paginación.
 *       - in: query
 *         name: offset
 *         schema:
 *           type: integer
 *           default: 0
 *         description: Offset de resultados para paginación.
 *       - in: query
 *         name: format
 *         schema:
 *           type: string
 *           enum: [objects, tuples]
 *           default: objects
 *         description: Formato de respuesta ("objects" para array de objetos o "tuples" para array de tuplas [archivo, cnthuevos, createdAt, updatedAt]).
 *     responses:
 *       200:
 *         description: Listado de registros obtenido exitosamente.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 total:
 *                   type: integer
 *                   example: 42
 *                 data:
 *                   type: array
 *                   items:
 *                     oneOf:
 *                       - $ref: '#/components/schemas/FileRecordObject'
 *                       - $ref: '#/components/schemas/FileRecordTuple'
 *       400:
 *         description: Parámetros de búsqueda inválidos.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ErrorResponse'
 */
router.get(
  '/records',
  validateQueryFilters,
  (req, res, next) => videoController.getRecords(req, res, next)
);

module.exports = router;
