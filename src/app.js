'use strict';

const express = require('express');
const morgan = require('morgan');
const swaggerUi = require('swagger-ui-express');
const swaggerSpec = require('./config/swagger');
const videoRoutes = require('./routes/video.routes');
const { errorHandler } = require('./middlewares/error.middleware');

const app = express();

// ─── Logger HTTP ─────────────────────────────────────────────────────────────
// 'dev'      → coloreado y compacto, ideal para desarrollo
// 'combined' → formato Apache completo, ideal para producción
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));

// ─── Parsers ─────────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ─── Documentación Swagger UI ────────────────────────────────────────────────
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// ─── Rutas ───────────────────────────────────────────────────────────────────
app.use('/api/videos', videoRoutes);

// ─── Health check ─────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ─── Ruta no encontrada ───────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ success: false, message: 'Ruta no encontrada.' });
});

// ─── Manejador global de errores ──────────────────────────────────────────────
app.use(errorHandler);

module.exports = app;
