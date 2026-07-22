'use strict';

require('dotenv').config();

const app = require('./app');
const { sequelize } = require('./config/database');

const PORT = process.env.PORT || 3000;

async function bootstrap() {
  try {
    // Verificar conexión a la base de datos
    await sequelize.authenticate();
    console.log('[DB] Conexión establecida correctamente.');

    // sync() crea la tabla si no existe; no modifica el schema en ejecución.
    // Para cambios de schema usar migrations (Sequelize CLI).
    await sequelize.sync();
    console.log('[DB] Modelos sincronizados.');

    app.listen(PORT, () => {
      console.log(`[SERVER] Servicio de Procesamiento corriendo en http://localhost:${PORT}`);
      console.log(`[SERVER] Entorno: ${process.env.NODE_ENV || 'development'}`);
    });
  } catch (error) {
    console.error('[SERVER] Error al iniciar la aplicación:', error);
    process.exit(1);
  }
}

bootstrap();
