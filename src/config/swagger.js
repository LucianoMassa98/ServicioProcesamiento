'use strict';

const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Servicio de Procesamiento de Videos y Conteo de Huevos',
      version: '1.0.0',
      description:
        'API REST para el análisis de videos de cintas transportadoras de huevos, consolidación diaria por galpón y registro de análisis.',
    },
    servers: [
      {
        url: 'http://localhost:3000',
        description: 'Servidor local de desarrollo',
      },
    ],
    components: {
      schemas: {
        VideoAnalysis: {
          type: 'object',
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              example: '3fa85f64-5717-4562-b3fc-2c963f66a700',
            },
            galponId: {
              type: 'string',
              format: 'uuid',
              example: 'e7b9a528-9844-42b7-8176-13a52e008d51',
            },
            name: {
              type: 'string',
              example: 'Video Galpón 1 - Mañana',
            },
            eggs: {
              type: 'integer',
              example: 120,
            },
            processedFrames: {
              type: 'integer',
              example: 1500,
            },
            processingTime: {
              type: 'number',
              format: 'float',
              example: 12.45,
            },
            status: {
              type: 'string',
              enum: ['pending', 'processing', 'completed', 'failed'],
              example: 'completed',
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-08-05T14:30:00.000Z',
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-08-05T14:30:05.000Z',
            },
          },
        },
        ConsolidatedDay: {
          type: 'object',
          properties: {
            fecha: {
              type: 'string',
              format: 'date',
              example: '2026-08-05',
            },
            galponId: {
              type: 'string',
              format: 'uuid',
              example: 'e7b9a528-9844-42b7-8176-13a52e008d51',
            },
            totalHuevos: {
              type: 'integer',
              example: 1450,
            },
            cantidadVideos: {
              type: 'integer',
              example: 12,
            },
          },
        },
        FileRecordObject: {
          type: 'object',
          properties: {
            archivo: {
              type: 'string',
              example: 'video_galpon1_01.mp4',
            },
            cnthuevos: {
              type: 'integer',
              example: 120,
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-08-05T14:30:00.000Z',
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-08-05T14:30:05.000Z',
            },
          },
        },
        FileRecordTuple: {
          type: 'array',
          items: {
            oneOf: [{ type: 'string' }, { type: 'integer' }],
          },
          example: [
            'video_galpon1_01.mp4',
            120,
            '2026-08-05T14:30:00.000Z',
            '2026-08-05T14:30:05.000Z',
          ],
        },
        ApiResponse: {
          type: 'object',
          properties: {
            success: {
              type: 'boolean',
              example: true,
            },
            message: {
              type: 'string',
              example: 'Operación realizada exitosamente.',
            },
          },
        },
        ErrorResponse: {
          type: 'object',
          properties: {
            success: {
              type: 'boolean',
              example: false,
            },
            message: {
              type: 'string',
              example: 'Mensaje explicativo del error.',
            },
            errors: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  field: { type: 'string', example: 'galponId' },
                  message: { type: 'string', example: 'El campo galponId debe ser un UUID v4 válido.' },
                },
              },
            },
          },
        },
      },
    },
  },
  apis: ['./src/routes/*.js'],
};

const swaggerSpec = swaggerJsdoc(options);

module.exports = swaggerSpec;
