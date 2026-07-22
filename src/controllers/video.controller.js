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
   * Recibe un video via multipart/form-data, lo analiza y devuelve el conteo.
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

      // ─── Ejecutar análisis ─────────────────────────────────────────────
      const record = await videoAnalysisService.analyze({ videoPath, galponId, name });

      // ─── Respuesta exitosa ─────────────────────────────────────────────
      return res.status(200).json({
        success: true,
        message: 'Video analizado correctamente.',
        data: {
          galponId: record.galponId,
          name: record.name,
          eggs: record.eggs,
          processedFrames: record.processedFrames,
          processingTime: record.processingTime,
        },
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new VideoController();
