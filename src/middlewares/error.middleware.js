'use strict';

/**
 * Manejador global de errores de Express.
 *
 * Captura errores no gestionados y devuelve una respuesta JSON uniforme.
 * Debe registrarse DESPUÉS de todas las rutas en app.js.
 */
function errorHandler(err, req, res, _next) {
  const statusCode = err.status || err.statusCode || 500;

  // Log del error (en producción usar un logger como Winston o Pino)
  if (process.env.NODE_ENV !== 'test') {
    console.error(`[ERROR] ${req.method} ${req.originalUrl} → ${statusCode}:`, err.message);
    if (process.env.NODE_ENV === 'development') {
      console.error(err.stack);
    }
  }

  res.status(statusCode).json({
    success: false,
    message: err.message || 'Error interno del servidor.',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
}

module.exports = { errorHandler };
