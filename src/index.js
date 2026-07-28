'use strict';

require('dotenv').config();

const app = require('./app');
const { sequelize } = require('./config/database');

const PORT = process.env.PORT || 3000;

// ─── Protección contra crashes por errores no capturados ─────────────────────
// Evita que un error en el script Python u otro proceso asíncrono
// derrumbe todo el servidor Node.js.
process.on('uncaughtException', (err) => {
  console.error('[FATAL] uncaughtException — el proceso continuará:', err);
});

process.on('unhandledRejection', (reason) => {
  console.error('[FATAL] unhandledRejection — el proceso continuará:', reason);
});

async function bootstrap() {
  try {
    // Verificar conexión a la base de datos
    await sequelize.authenticate();
    console.log('[DB] Conexión establecida correctamente.');

    // sync() crea la tabla si no existe; no modifica el schema en ejecución.
    // Para cambios de schema usar migrations (Sequelize CLI).
    await sequelize.sync();
    console.log('[DB] Modelos sincronizados.');

    // Escuchar en 0.0.0.0 para que Railway pueda enrutar el tráfico
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`[SERVER] Servicio de Procesamiento corriendo en http://0.0.0.0:${PORT}`);
      console.log(`[SERVER] Entorno: ${process.env.NODE_ENV || 'development'}`);
    });
  } catch (error) {
    console.error('[SERVER] Error al iniciar la aplicación:', error);
    process.exit(1);
  }
}

bootstrap();
