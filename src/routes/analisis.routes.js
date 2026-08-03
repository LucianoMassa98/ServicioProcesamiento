'use strict';

const { Router } = require('express');
const { param, query } = require('express-validator');
const analisisController = require('../controllers/analisis.controller');

const router = Router();

// ─── Validadores reutilizables ────────────────────────────────────────────────

/** Valida un query param de fecha ISO (YYYY-MM-DD) si viene presente. */
const validarFecha = (campo) =>
  query(campo)
    .optional()
    .isISO8601()
    .withMessage(`El parámetro "${campo}" debe ser una fecha válida (YYYY-MM-DD).`);

/** Valida un UUID v4 como query param si viene presente. */
const validarGalponIdQuery = query('galponId')
  .optional()
  .isUUID(4)
  .withMessage('El parámetro "galponId" debe ser un UUID v4 válido.');

/** Valida paginación. */
const validarPaginacion = [
  query('pagina')
    .optional()
    .isInt({ min: 1 })
    .withMessage('El parámetro "pagina" debe ser un entero mayor a 0.')
    .toInt(),
  query('limite')
    .optional()
    .isInt({ min: 1, max: 100 })
    .withMessage('El parámetro "limite" debe ser un entero entre 1 y 100.')
    .toInt(),
];

// ─── Rutas ────────────────────────────────────────────────────────────────────

/**
 * @openapi
 * /api/analisis/huevos/por-dia:
 *   get:
 *     summary: Cantidad total de huevos agrupada por día
 *     tags:
 *       - Análisis e Informes
 *     parameters:
 *       - in: query
 *         name: desde
 *         schema:
 *           type: string
 *           format: date
 *         example: 2026-07-01
 *         description: Fecha inicial del rango (YYYY-MM-DD)
 *       - in: query
 *         name: hasta
 *         schema:
 *           type: string
 *           format: date
 *         example: 2026-07-31
 *         description: Fecha final del rango (YYYY-MM-DD)
 *       - in: query
 *         name: galponId
 *         schema:
 *           type: string
 *           format: uuid
 *         description: UUID del galpón a filtrar
 *     responses:
 *       200:
 *         description: Reporte diario de huevos generado exitosamente
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
 *                   example: 5
 *                 data:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       fecha:
 *                         type: string
 *                         example: '2026-07-29'
 *                       totalHuevos:
 *                         type: integer
 *                         example: 350
 *                       cantidadAnalisis:
 *                         type: integer
 *                         example: 8
 */
router.get(
  '/huevos/por-dia',
  [validarFecha('desde'), validarFecha('hasta'), validarGalponIdQuery],
  (req, res, next) => analisisController.huevosPorDia(req, res, next)
);

/**
 * @openapi
 * /api/analisis/huevos/resumen:
 *   get:
 *     summary: Resumen estadístico global de producción
 *     tags:
 *       - Análisis e Informes
 *     parameters:
 *       - in: query
 *         name: desde
 *         schema:
 *           type: string
 *           format: date
 *       - in: query
 *         name: hasta
 *         schema:
 *           type: string
 *           format: date
 *       - in: query
 *         name: galponId
 *         schema:
 *           type: string
 *           format: uuid
 *     responses:
 *       200:
 *         description: Métricas y resumen estadístico global
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 data:
 *                   type: object
 *                   properties:
 *                     totalHuevos:
 *                       type: integer
 *                       example: 1250
 *                     totalAnalisis:
 *                       type: integer
 *                       example: 25
 *                     promedioHuevosPorAnalisis:
 *                       type: number
 *                       example: 50.0
 *                     maxHuevosEnUnAnalisis:
 *                       type: integer
 *                       example: 120
 *                     minHuevosEnUnAnalisis:
 *                       type: integer
 *                       example: 5
 *                     tiempoTotalProcesamientoSeg:
 *                       type: number
 *                       example: 350.45
 *                     promedioTiempoProcesamientoSeg:
 *                       type: number
 *                       example: 14.02
 *                     diaMasProductivo:
 *                       type: object
 *                       properties:
 *                         fecha:
 *                           type: string
 *                           example: '2026-07-28'
 *                         totalHuevos:
 *                           type: integer
 *                           example: 480
 */
router.get(
  '/huevos/resumen',
  [validarFecha('desde'), validarFecha('hasta'), validarGalponIdQuery],
  (req, res, next) => analisisController.resumenGlobal(req, res, next)
);

/**
 * @openapi
 * /api/analisis/huevos/por-galpon:
 *   get:
 *     summary: Totales de producción comparados por galpón
 *     tags:
 *       - Análisis e Informes
 *     parameters:
 *       - in: query
 *         name: desde
 *         schema:
 *           type: string
 *           format: date
 *       - in: query
 *         name: hasta
 *         schema:
 *           type: string
 *           format: date
 *     responses:
 *       200:
 *         description: Listado comparativo entre galpones
 */
router.get(
  '/huevos/por-galpon',
  [validarFecha('desde'), validarFecha('hasta')],
  (req, res, next) => analisisController.huevosPorGalpon(req, res, next)
);

/**
 * @openapi
 * /api/analisis/estado/conteo:
 *   get:
 *     summary: Conteo de análisis agrupados por estado
 *     tags:
 *       - Análisis e Informes
 *     responses:
 *       200:
 *         description: Conteo de tareas por estado
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 data:
 *                   type: object
 *                   properties:
 *                     pending:
 *                       type: integer
 *                       example: 0
 *                     processing:
 *                       type: integer
 *                       example: 1
 *                     completed:
 *                       type: integer
 *                       example: 24
 *                     failed:
 *                       type: integer
 *                       example: 0
 */
router.get(
  '/estado/conteo',
  (req, res, next) => analisisController.conteoPorEstado(req, res, next)
);

/**
 * @openapi
 * /api/analisis/listado:
 *   get:
 *     summary: Listado paginado de análisis con filtros
 *     tags:
 *       - Análisis e Informes
 *     parameters:
 *       - in: query
 *         name: pagina
 *         schema:
 *           type: integer
 *           default: 1
 *       - in: query
 *         name: limite
 *         schema:
 *           type: integer
 *           default: 20
 *       - in: query
 *         name: galponId
 *         schema:
 *           type: string
 *           format: uuid
 *       - in: query
 *         name: status
 *         schema:
 *           type: string
 *           enum: [pending, processing, completed, failed]
 *       - in: query
 *         name: desde
 *         schema:
 *           type: string
 *           format: date
 *       - in: query
 *         name: hasta
 *         schema:
 *           type: string
 *           format: date
 *     responses:
 *       200:
 *         description: Lista de análisis paginada
 */
router.get(
  '/listado',
  [
    ...validarPaginacion,
    validarGalponIdQuery,
    query('status')
      .optional()
      .isIn(['pending', 'processing', 'completed', 'failed'])
      .withMessage('El parámetro "status" debe ser: pending, processing, completed o failed.'),
    validarFecha('desde'),
    validarFecha('hasta'),
  ],
  (req, res, next) => analisisController.listado(req, res, next)
);

/**
 * @openapi
 * /api/analisis/{id}:
 *   get:
 *     summary: Obtener el detalle de un análisis específico
 *     tags:
 *       - Análisis e Informes
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: string
 *           format: uuid
 *         description: UUID único del análisis
 *     responses:
 *       200:
 *         description: Detalle del análisis encontrado
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 data:
 *                   $ref: '#/components/schemas/VideoAnalysis'
 *       404:
 *         description: Análisis no encontrado
 */
router.get(
  '/:id',
  [
    param('id')
      .isUUID(4)
      .withMessage('El parámetro "id" debe ser un UUID v4 válido.'),
  ],
  (req, res, next) => analisisController.detalle(req, res, next)
);

module.exports = router;
