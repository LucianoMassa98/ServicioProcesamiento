'use strict';

const { validationResult } = require('express-validator');
const fs = require('fs/promises');
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

      // Crear el registro antes de procesar para que siempre quede trazabilidad en DB.
      const analysisRecord = await videoAnalysisService.createPendingAnalysis({ galponId, name });

      // ─── Respuesta inmediata ───────────────────────────────────────────
      res.status(200).json({
        success: true,
        message: 'Video recibido. El análisis está en proceso.',
        analysisId: analysisRecord.id,
      });

      // ─── Análisis en background (fire-and-forget) ──────────────────────
      videoAnalysisService.analyze({ videoPath, analysisId: analysisRecord.id }).catch((err) => {
        console.error('[VideoController] Error en análisis en background:', err.message);
      });
    } catch (error) {
      if (req.file?.path) {
        await fs.unlink(req.file.path).catch(() => {});
      }
      next(error);
    }
  }
}

module.exports = new VideoController();
