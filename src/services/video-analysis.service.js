'use strict';

const fs = require('fs/promises');
const { Op } = require('sequelize');
const { sequelize } = require('../config/database');
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
   * Obtiene la información consolidada por día y galpón (cantidad total de huevos contados).
   *
   * @param {object} params
   * @param {string} [params.galponId]  - Identificador único del galpón.
   * @param {string} [params.date]      - Día específico en formato YYYY-MM-DD.
   * @param {string} [params.startDate] - Fecha inicial en formato YYYY-MM-DD.
   * @param {string} [params.endDate]   - Fecha final en formato YYYY-MM-DD.
   * @returns {Promise<Array<{fecha: string, galponId: string, totalHuevos: number, cantidadVideos: number}>>}
   */
  async getConsolidatedByDay({ galponId, date, startDate, endDate } = {}) {
    const where = this._buildWhereConditions({ galponId, date, startDate, endDate });

    const results = await VideoAnalysis.findAll({
      attributes: [
        [sequelize.fn('DATE', sequelize.col('created_at')), 'fecha'],
        'galponId',
        [sequelize.fn('SUM', sequelize.col('eggs')), 'totalHuevos'],
        [sequelize.fn('COUNT', sequelize.col('id')), 'cantidadVideos'],
      ],
      where,
      group: [sequelize.fn('DATE', sequelize.col('created_at')), 'galponId'],
      order: [[sequelize.fn('DATE', sequelize.col('created_at')), 'DESC']],
      raw: true,
    });

    return results.map((row) => ({
      fecha: row.fecha,
      galponId: row.galponId,
      totalHuevos: parseInt(row.totalHuevos || 0, 10),
      cantidadVideos: parseInt(row.cantidadVideos || 0, 10),
    }));
  }

  /**
   * Devuelve los registros formateados como [archivo, cnthuevos, createdAt, updatedAt].
   *
   * @param {object} params
   * @param {string} [params.galponId]
   * @param {string} [params.startDate]
   * @param {string} [params.endDate]
   * @param {number} [params.limit=50]
   * @param {number} [params.offset=0]
   * @param {string} [params.format='objects'] - 'objects' | 'tuples'
   * @returns {Promise<{total: number, data: Array}>}
   */
  async getFileRecords({ galponId, date, startDate, endDate, limit = 50, offset = 0, format = 'objects' } = {}) {
    const where = this._buildWhereConditions({ galponId, date, startDate, endDate });

    const { count, rows } = await VideoAnalysis.findAndCountAll({
      attributes: ['name', 'eggs', 'createdAt', 'updatedAt'],
      where,
      order: [['createdAt', 'DESC']],
      limit: parseInt(limit, 10),
      offset: parseInt(offset, 10),
      raw: true,
    });

    const isTuples = format === 'tuples' || format === 'array';

    const data = rows.map((row) => {
      if (isTuples) {
        return [row.name, row.eggs, row.createdAt, row.updatedAt];
      }
      return {
        archivo: row.name,
        cnthuevos: row.eggs,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      };
    });

    return { total: count, data };
  }

  /**
   * Construye las condiciones de búsqueda en base a galponId y rango de fechas.
   *
   * @private
   */
  _buildWhereConditions({ galponId, date, startDate, endDate }) {
    const where = { status: 'completed' };

    if (galponId) {
      where.galponId = galponId;
    }

    if (date) {
      where.createdAt = {
        [Op.gte]: new Date(`${date}T00:00:00.000Z`),
        [Op.lte]: new Date(`${date}T23:59:59.999Z`),
      };
    } else if (startDate || endDate) {
      where.createdAt = {};
      if (startDate) {
        where.createdAt[Op.gte] = new Date(`${startDate}T00:00:00.000Z`);
      }
      if (endDate) {
        where.createdAt[Op.lte] = new Date(`${endDate}T23:59:59.999Z`);
      }
    }

    return where;
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
