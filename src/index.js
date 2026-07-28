'use strict';

require('dotenv').config();

const app = require('./app');
const { sequelize } = require('./config/database');

const PORT = process.env.PORT || 3000;

// ─── Protección contra crashes por errores no capturados ─────────────────────
process.on('uncaughtException', (err) => {
  console.error('[FATAL] uncaughtException — el proceso continuará:', err);
});

process.on('unhandledRejection', (reason) => {
  console.error('[FATAL] unhandledRejection — el proceso continuará:', reason);
});

// ─── Arrancar el servidor PRIMERO ─────────────────────────────────────────────
// Railway necesita ver el puerto activo para marcar el deploy como exitoso.
// La conexión a la DB se intenta después, en segundo plano.
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`[SERVER] Escuchando en http://0.0.0.0:${PORT}`);
  console.log(`[SERVER] Entorno: ${process.env.NODE_ENV || 'development'}`);
  console.log(`[SERVER] PYTHON_BIN: ${process.env.PYTHON_BIN || 'python3 (default)'}`);
});

// ─── Conectar la base de datos en background ──────────────────────────────────
async function connectDatabase(retries = 5, delayMs = 3000) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      await sequelize.authenticate();
      console.log('[DB] Conexión establecida correctamente.');
      await sequelize.sync();
      console.log('[DB] Modelos sincronizados.');
      return;
    } catch (error) {
      console.error(`[DB] Intento ${attempt}/${retries} fallido:`, error.message);
      if (attempt < retries) {
        console.log(`[DB] Reintentando en ${delayMs / 1000}s...`);
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      } else {
        console.error('[DB] No se pudo conectar a la base de datos. Las rutas que dependen de DB retornarán error.');
      }
    }
  }
}

connectDatabase();
