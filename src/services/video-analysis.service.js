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
 *  1. Crea el registro de análisis en DB antes de iniciar el procesamiento.
 *  2. Delega el conteo al EggCounterService (inyectado por constructor).
 *  3. Actualiza el estado y las métricas del registro según el resultado.
 *  4. Elimina el archivo temporal independientemente del resultado.
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
  async createPendingAnalysis({ galponId, name }) {
    return VideoAnalysis.create({
      galponId,
      name,
      status: 'processing',
    });
  }

  async analyze({ videoPath, analysisId }) {
    const record = await VideoAnalysis.findByPk(analysisId);
    if (!record) {
      throw new Error(`No se encontró el análisis con id "${analysisId}" para actualizar.`);
    }

    console.log(`[VideoAnalysisService] Iniciando análisis id=${analysisId} video=${videoPath}`);

    let countResult;
    try {
      countResult = await this.eggCounterService.countEggs(videoPath);
      await record.update({
        eggs: countResult.eggs,
        processedFrames: countResult.processedFrames,
        processingTime: countResult.processingTime,
        status: 'completed',
      });
      console.log(`[VideoAnalysisService] Análisis id=${analysisId} completado. eggs=${countResult.eggs} frames=${countResult.processedFrames} time=${countResult.processingTime}s`);
    } catch (error) {
      await record.update({ status: 'failed' }).catch((updateError) => {
        console.error(
          '[VideoAnalysisService] No se pudo actualizar el estado a failed:',
          updateError.message
        );
      });
      console.error(`[VideoAnalysisService] Error en análisis id=${analysisId}:`, error.message);
      throw error;
    } finally {
      await this._deleteTemporaryFile(videoPath);
    }

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
