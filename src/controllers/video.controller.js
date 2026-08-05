'use strict';

const { validationResult } = require('express-validator');
const VideoAnalysisService = require('../services/video-analysis.service');

const videoAnalysisService = new VideoAnalysisService();

/**
 * VideoController
 *
 * Responsabilidad: manejar las peticiones HTTP del dominio de video.
 * Delega toda la lógica de negocio a VideoAnalysisService.
 */
class VideoController {
  /**
   * POST /api/videos/analyze
   *
   * Recibe un video via multipart/form-data y responde inmediatamente.
   * El análisis (conteo + persistencia en DB) corre en background.
   *
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {import('express').NextFunction} next
   */
  async analyze(req, res, next) {
    try {
      // ─── Validar errores de express-validator ──────────────────────────
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({
          success: false,
          message: 'Datos de entrada inválidos.',
          errors: errors.array().map((e) => ({ field: e.path, message: e.msg })),
        });
      }

      // ─── Verificar que el archivo fue recibido ─────────────────────────
      if (!req.file) {
        return res.status(400).json({
          success: false,
          message: 'El campo "file" es obligatorio y debe ser un archivo de video.',
        });
      }

      const { name, galponId } = req.body;
      const videoPath = req.file.path;

      // ─── Respuesta inmediata ───────────────────────────────────────────
      // El análisis es costoso (Python + OpenCV). Respondemos de inmediato
      // y dejamos que el procesamiento ocurra en segundo plano.
      res.status(200).json({
        success: true,
        message: 'Video recibido. El análisis está en proceso.',
      });

      // ─── Análisis en background (fire-and-forget) ──────────────────────
      videoAnalysisService.analyze({ videoPath, galponId, name }).catch((err) => {
        console.error('[VideoController] Error en análisis en background:', err.message);
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * GET /api/videos/consolidated
   *
   * Retorna información consolidada por día y galpón (cantidad total de huevos).
   *
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {import('express').NextFunction} next
   */
  async getConsolidated(req, res, next) {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({
          success: false,
          message: 'Parámetros de búsqueda inválidos.',
          errors: errors.array().map((e) => ({ field: e.path, message: e.msg })),
        });
      }

      const { galponId, date, startDate, endDate } = req.query;

      const data = await videoAnalysisService.getConsolidatedByDay({
        galponId,
        date,
        startDate,
        endDate,
      });

      return res.status(200).json({
        success: true,
        data,
      });
    } catch (error) {
      next(error);
    }
  }

  /**
   * GET /api/videos/records
   *
   * Retorna registros de análisis en formato [archivo, cnthuevos, createdAt, updatedAt]
   * u objetos correspondientes.
   *
   * @param {import('express').Request} req
   * @param {import('express').Response} res
   * @param {import('express').NextFunction} next
   */
  async getRecords(req, res, next) {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({
          success: false,
          message: 'Parámetros de búsqueda inválidos.',
          errors: errors.array().map((e) => ({ field: e.path, message: e.msg })),
        });
      }

      const { galponId, date, startDate, endDate, limit, offset, format } = req.query;

      const result = await videoAnalysisService.getFileRecords({
        galponId,
        date,
        startDate,
        endDate,
        limit,
        offset,
        format,
      });

      return res.status(200).json({
        success: true,
        total: result.total,
        data: result.data,
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new VideoController();
