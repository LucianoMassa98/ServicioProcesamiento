'use strict';

const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/database');

/**
 * Modelo VideoAnalysis
 *
 * Almacena únicamente el resultado del análisis.
 * NO almacena rutas ni archivos de video.
 */
const VideoAnalysis = sequelize.define(
  'VideoAnalysis',
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
      allowNull: false,
      comment: 'Identificador único del análisis',
    },
    galponId: {
      type: DataTypes.UUID,
      allowNull: false,
      field: 'galpon_id',
      comment: 'Identificador del galpón al que pertenece el análisis',
      validate: {
        isUUID: 4,
        notNull: { msg: 'galponId es obligatorio.' },
      },
    },
    name: {
      type: DataTypes.STRING(255),
      allowNull: false,
      comment: 'Nombre descriptivo del análisis',
      validate: {
        notEmpty: { msg: 'name no puede estar vacío.' },
        len: {
          args: [1, 255],
          msg: 'name debe tener entre 1 y 255 caracteres.',
        },
      },
    },
    eggs: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 0,
      comment: 'Total de huevos contados',
      validate: {
        min: { args: [0], msg: 'eggs no puede ser negativo.' },
      },
    },
    processedFrames: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 0,
      field: 'processed_frames',
      comment: 'Cantidad de fotogramas procesados',
    },
    processingTime: {
      type: DataTypes.FLOAT,
      allowNull: false,
      defaultValue: 0,
      field: 'processing_time',
      comment: 'Tiempo de procesamiento en segundos',
    },
    status: {
      type: DataTypes.STRING(20),
      allowNull: false,
      defaultValue: 'completed',
      comment: 'Estado del análisis',
      validate: {
        isIn: {
          args: [['pending', 'processing', 'completed', 'failed']],
          msg: 'status debe ser: pending, processing, completed o failed.',
        },
      },
    },
  },
  {
    tableName: 'video_analysis',
    timestamps: true,
    underscored: true,
    comment: 'Resultados de análisis de video de cinta transportadora de huevos',
  }
);

module.exports = VideoAnalysis;
