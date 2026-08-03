'use strict';

const { Op, fn, col } = require('sequelize');
const VideoAnalysis = require('../models/video-analysis.model');

/**
 * AnalisisController
 *
 * Endpoints informativos sobre conteos de huevos y análisis almacenados.
 * Todos los endpoints son de sólo lectura (GET).
 */
class AnalisisController {
  /**
   * Helper privado para construir el filtro de rango de fechas de Sequelize.
   * Maneja tanto strings ("YYYY-MM-DD" / ISO) como objetos Date de JS de forma segura.
   *
   * @private
   * @param {string|Date} [desde]
   * @param {string|Date} [hasta]
   * @returns {object|undefined} Objeto de filtro para `createdAt` o undefined si no hay fechas.
   */
  _construirFiltroFecha(desde, hasta) {
    if (!desde && !hasta) return undefined;
    const filtro = {};

    if (desde) {
      const isoStr = desde instanceof Date ? desde.toISOString().split('T')[0] : String(desde).trim().split('T')[0];
      const d = new Date(`${isoStr}T00:00:00.000Z`);
      if (!isNaN(d.getTime())) {
        filtro[Op.gte] = d;
      }
    }

    if (hasta) {
      const isoStr = hasta instanceof Date ? hasta.toISOString().split('T')[0] : String(hasta).trim().split('T')[0];
      const h = new Date(`${isoStr}T23:59:59.999Z`);
      if (!isNaN(h.getTime())) {
        filtro[Op.lte] = h;
      }
    }

    return Object.keys(filtro).length > 0 ? filtro : undefined;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/huevos/por-dia
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Devuelve la cantidad total de huevos agrupada por día.
   *
   * Query params opcionales:
   *  - desde   ISO date  Inicio del rango (inclusive). Ej: 2025-01-01
   *  - hasta   ISO date  Fin del rango   (inclusive). Ej: 2025-01-31
   *  - galponId UUID     Filtra por galpón específico.
   */
  async huevosPorDia(req, res, next) {
    try {
      const { desde, hasta, galponId } = req.query;

      const where = { status: 'completed' };
      if (galponId) where.galponId = galponId;

      const filtroFecha = this._construirFiltroFecha(desde, hasta);
      if (filtroFecha) where.createdAt = filtroFecha;

      const rows = await VideoAnalysis.findAll({
        attributes: [
          [fn('DATE', col('created_at')), 'fecha'],
          [fn('SUM', col('eggs')), 'totalHuevos'],
          [fn('COUNT', col('id')), 'cantidadAnalisis'],
        ],
        where,
        group: [fn('DATE', col('created_at'))],
        order: [[fn('DATE', col('created_at')), 'ASC']],
        raw: true,
      });

      res.json({
        success: true,
        total: rows.length,
        data: rows.map((r) => ({
          fecha: r.fecha,
          totalHuevos: Number(r.totalHuevos),
          cantidadAnalisis: Number(r.cantidadAnalisis),
        })),
      });
    } catch (error) {
      next(error);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/huevos/resumen
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Resumen global: total huevos, promedio diario, día más productivo, etc.
   *
   * Query params opcionales: desde, hasta, galponId (igual que huevosPorDia).
   */
  async resumenGlobal(req, res, next) {
    try {
      const { desde, hasta, galponId } = req.query;

      const where = { status: 'completed' };
      if (galponId) where.galponId = galponId;

      const filtroFecha = this._construirFiltroFecha(desde, hasta);
      if (filtroFecha) where.createdAt = filtroFecha;

      const [resumen, maximo] = await Promise.all([
        // Totales globales
        VideoAnalysis.findOne({
          attributes: [
            [fn('SUM', col('eggs')), 'totalHuevos'],
            [fn('AVG', col('eggs')), 'promedioHuevosPorAnalisis'],
            [fn('MAX', col('eggs')), 'maxHuevosEnUnAnalisis'],
            [fn('MIN', col('eggs')), 'minHuevosEnUnAnalisis'],
            [fn('COUNT', col('id')), 'totalAnalisis'],
            [fn('SUM', col('processing_time')), 'tiempoTotalProcesamientoSeg'],
            [fn('AVG', col('processing_time')), 'promedioTiempoProcesamientoSeg'],
          ],
          where,
          raw: true,
        }),

        // Día con más huevos
        VideoAnalysis.findOne({
          attributes: [
            [fn('DATE', col('created_at')), 'fecha'],
            [fn('SUM', col('eggs')), 'totalHuevos'],
          ],
          where,
          group: [fn('DATE', col('created_at'))],
          order: [[fn('SUM', col('eggs')), 'DESC']],
          limit: 1,
          raw: true,
        }),
      ]);

      res.json({
        success: true,
        data: {
          totalHuevos: Number(resumen?.totalHuevos ?? 0),
          totalAnalisis: Number(resumen?.totalAnalisis ?? 0),
          promedioHuevosPorAnalisis: parseFloat(
            Number(resumen?.promedioHuevosPorAnalisis ?? 0).toFixed(2)
          ),
          maxHuevosEnUnAnalisis: Number(resumen?.maxHuevosEnUnAnalisis ?? 0),
          minHuevosEnUnAnalisis: Number(resumen?.minHuevosEnUnAnalisis ?? 0),
          tiempoTotalProcesamientoSeg: parseFloat(
            Number(resumen?.tiempoTotalProcesamientoSeg ?? 0).toFixed(2)
          ),
          promedioTiempoProcesamientoSeg: parseFloat(
            Number(resumen?.promedioTiempoProcesamientoSeg ?? 0).toFixed(2)
          ),
          diaMasProductivo: maximo
            ? { fecha: maximo.fecha, totalHuevos: Number(maximo.totalHuevos) }
            : null,
        },
      });
    } catch (error) {
      next(error);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/huevos/por-galpon
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Totales de huevos agrupados por galponId.
   * Útil para comparar producción entre galpones.
   *
   * Query params opcionales: desde, hasta.
   */
  async huevosPorGalpon(req, res, next) {
    try {
      const { desde, hasta } = req.query;

      const where = { status: 'completed' };
      const filtroFecha = this._construirFiltroFecha(desde, hasta);
      if (filtroFecha) where.createdAt = filtroFecha;

      const rows = await VideoAnalysis.findAll({
        attributes: [
          'galponId',
          [fn('SUM', col('eggs')), 'totalHuevos'],
          [fn('COUNT', col('id')), 'cantidadAnalisis'],
          [fn('AVG', col('eggs')), 'promedioHuevos'],
          [fn('MAX', col('created_at')), 'ultimoAnalisis'],
        ],
        where,
        group: ['galpon_id'],
        order: [[fn('SUM', col('eggs')), 'DESC']],
        raw: true,
      });

      res.json({
        success: true,
        total: rows.length,
        data: rows.map((r) => ({
          galponId: r.galponId,
          totalHuevos: Number(r.totalHuevos),
          cantidadAnalisis: Number(r.cantidadAnalisis),
          promedioHuevos: parseFloat(Number(r.promedioHuevos).toFixed(2)),
          ultimoAnalisis: r.ultimoAnalisis,
        })),
      });
    } catch (error) {
      next(error);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/listado
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Lista paginada de análisis individuales con filtros.
   *
   * Query params:
   *  - pagina    number  Número de página (default: 1)
   *  - limite    number  Registros por página (default: 20, max: 100)
   *  - galponId  UUID    Filtrar por galpón.
   *  - status    string  Filtrar por estado (pending|processing|completed|failed).
   *  - desde     ISO date
   *  - hasta     ISO date
   */
  async listado(req, res, next) {
    try {
      const pagina = Math.max(1, parseInt(req.query.pagina, 10) || 1);
      const limite = Math.min(100, Math.max(1, parseInt(req.query.limite, 10) || 20));
      const { galponId, status, desde, hasta } = req.query;

      const where = {};
      if (galponId) where.galponId = galponId;
      if (status) where.status = status;

      const filtroFecha = this._construirFiltroFecha(desde, hasta);
      if (filtroFecha) where.createdAt = filtroFecha;

      const { count, rows } = await VideoAnalysis.findAndCountAll({
        where,
        order: [['createdAt', 'DESC']],
        limit: limite,
        offset: (pagina - 1) * limite,
      });

      res.json({
        success: true,
        paginacion: {
          paginaActual: pagina,
          limite,
          totalRegistros: count,
          totalPaginas: Math.ceil(count / limite),
        },
        data: rows,
      });
    } catch (error) {
      next(error);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/:id
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Detalle de un análisis individual por su UUID.
   */
  async detalle(req, res, next) {
    try {
      const { id } = req.params;

      const registro = await VideoAnalysis.findByPk(id);

      if (!registro) {
        return res.status(404).json({
          success: false,
          message: `No se encontró un análisis con id "${id}".`,
        });
      }

      res.json({ success: true, data: registro });
    } catch (error) {
      next(error);
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // GET /api/analisis/estado/conteo
  // ──────────────────────────────────────────────────────────────────────────
  /**
   * Cantidad de análisis agrupados por estado (pending, processing, completed, failed).
   */
  async conteoPorEstado(req, res, next) {
    try {
      const rows = await VideoAnalysis.findAll({
        attributes: [
          'status',
          [fn('COUNT', col('id')), 'cantidad'],
        ],
        group: ['status'],
        raw: true,
      });

      const resultado = { pending: 0, processing: 0, completed: 0, failed: 0 };
      rows.forEach((r) => {
        resultado[r.status] = Number(r.cantidad);
      });

      res.json({ success: true, data: resultado });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = new AnalisisController();
