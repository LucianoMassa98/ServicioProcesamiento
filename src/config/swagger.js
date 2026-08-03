'use strict';

const swaggerJSDoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Servicio de Procesamiento API',
      version: '1.0.0',
      description:
        'API REST para el conteo de huevos en cintas transportadoras mediante análisis de video y consulta de estadísticas de producción.',
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
              example: '550e8400-e29b-41d4-a716-446655440000',
              description: 'Identificador único del análisis',
            },
            galponId: {
              type: 'string',
              format: 'uuid',
              example: 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
              description: 'UUID del galpón',
            },
            name: {
              type: 'string',
              example: 'Cinta A - Turno Mañana',
              description: 'Nombre descriptivo del análisis',
            },
            eggs: {
              type: 'integer',
              example: 42,
              description: 'Total de huevos contados',
            },
            processedFrames: {
              type: 'integer',
              example: 1200,
              description: 'Fotogramas procesados',
            },
            processingTime: {
              type: 'number',
              format: 'float',
              example: 14.52,
              description: 'Tiempo de procesamiento en segundos',
            },
            status: {
              type: 'string',
              enum: ['pending', 'processing', 'completed', 'failed'],
              example: 'completed',
              description: 'Estado del análisis',
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-07-29T18:00:00.000Z',
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              example: '2026-07-29T18:00:15.000Z',
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
              example: 'Datos de entrada inválidos.',
            },
            errors: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  field: { type: 'string', example: 'galponId' },
                  message: { type: 'string', example: 'El campo "galponId" es obligatorio.' },
                },
              },
            },
          },
        },
      },
    },
  },
  apis: ['./src/routes/*.routes.js'],
};

const swaggerSpec = swaggerJSDoc(options);

function setupSwagger(app) {
  app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
  console.log('[SWAGGER] Documentación disponible en /api-docs');
}

module.exports = setupSwagger;
