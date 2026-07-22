'use strict';

const express = require('express');
const videoRoutes = require('./routes/video.routes');
const { errorHandler } = require('./middlewares/error.middleware');

const app = express();

// ─── Parsers ─────────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

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
