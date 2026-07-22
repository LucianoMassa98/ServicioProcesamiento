'use strict';

const fs = require('fs/promises');
const EggCounterService = require('./egg-counter.service');
const VideoAnalysis = require('../models/video-analysis.model');

/**
 * VideoAnalysisService
 *
 * Responsabilidad: orquestar el análisis completo de un video.
 *
 * Flujo:
 *  1. Delega el conteo al EggCounterService (inyectado por constructor).
 *  2. Elimina el archivo temporal independientemente del resultado.
 *  3. Persiste únicamente el resultado en la base de datos.
 *  4. Retorna el registro creado.
 *
 * Principio de Inversión de Dependencias (DIP):
 *  Recibe EggCounterService por inyección de dependencias, lo que permite
 *  sustituirlo por un mock en tests o por una implementación YOLO en producción
 *  sin modificar este servicio.
 */
class VideoAnalysisService {
  /**
   * @param {EggCounterService} eggCounterService - Servicio de conteo de huevos.
   */
  constructor(eggCounterService = new EggCounterService()) {
    this.eggCounterService = eggCounterService;
  }

  /**
   * Analiza el video y persiste el resultado.
   *
   * @param {object} params
   * @param {string} params.videoPath  - Ruta temporal del video.
   * @param {string} params.galponId   - UUID del galpón.
   * @param {string} params.name       - Nombre descriptivo del análisis.
   * @returns {Promise<VideoAnalysis>} Registro creado en la base de datos.
   */
  async analyze({ videoPath, galponId, name }) {
    let countResult;

    try {
      // Ejecutar conteo de huevos
      countResult = await this.eggCounterService.countEggs(videoPath);
    } finally {
      // Garantizar eliminación del temporal incluso si el análisis falla
      await this._deleteTemporaryFile(videoPath);
    }

    // Persistir resultado (sin ruta de video)
    const record = await VideoAnalysis.create({
      galponId,
      name,
      eggs: countResult.eggs,
      processedFrames: countResult.processedFrames,
      processingTime: countResult.processingTime,
      status: 'completed',
    });

    return record;
  }

  /**
   * Elimina el archivo temporal de forma segura.
   * Registra advertencia si el archivo no existe, pero no lanza error.
   *
   * @private
   * @param {string} filePath
   */
  async _deleteTemporaryFile(filePath) {
    try {
      await fs.unlink(filePath);
      console.log(`[VideoAnalysisService] Archivo temporal eliminado: ${filePath}`);
    } catch (err) {
      if (err.code !== 'ENOENT') {
        console.warn(
          `[VideoAnalysisService] No se pudo eliminar el archivo temporal "${filePath}":`,
          err.message
        );
      }
    }
  }
}

module.exports = VideoAnalysisService;
