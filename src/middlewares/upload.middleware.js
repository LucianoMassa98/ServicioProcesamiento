'use strict';

const multer = require('multer');
const path = require('path');
const os = require('os');

// ─── Configuración de tamaño máximo ──────────────────────────────────────────
const MAX_FILE_SIZE_MB = parseInt(process.env.MAX_FILE_SIZE_MB || '500', 10);
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// ─── Formatos de video permitidos ─────────────────────────────────────────────
const ALLOWED_MIME_TYPES = new Set([
  'video/mp4',
  'video/quicktime',       // .mov
  'video/x-msvideo',       // .avi
  'video/x-matroska',      // .mkv
  'video/avi',
]);

const ALLOWED_EXTENSIONS = new Set(['.mp4', '.mov', '.avi', '.mkv']);

/**
 * Filtro de archivos: valida tipo MIME y extensión.
 */
function fileFilter(_req, file, callback) {
  const ext = path.extname(file.originalname).toLowerCase();

  if (!ALLOWED_MIME_TYPES.has(file.mimetype) && !ALLOWED_EXTENSIONS.has(ext)) {
    const error = new Error(
      `Formato de archivo no soportado. Formatos permitidos: mp4, mov, avi, mkv.`
    );
    error.status = 415;
    return callback(error, false);
  }

  callback(null, true);
}

const fs = require('fs');

// ─── Directorio temporal local (evita usar /tmp en RAM en Docker) ───────────
const TEMP_DIR = path.resolve(__dirname, '../../tmp');
if (!fs.existsSync(TEMP_DIR)) {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

/**
 * Limpia archivos temporales antiguos (> 10 minutos) que hayan quedado abandonados.
 */
function cleanStaleTempFiles() {
  try {
    const files = fs.readdirSync(TEMP_DIR);
    const now = Date.now();
    for (const file of files) {
      if (file.startsWith('egg-video-')) {
        const filePath = path.join(TEMP_DIR, file);
        const stats = fs.statSync(filePath);
        if (now - stats.mtimeMs > 10 * 60 * 1000) {
          fs.unlinkSync(filePath);
          console.log(`[UploadMiddleware] Limpieza de archivo huérfano: ${file}`);
        }
      }
    }
  } catch (err) {
    // Ignorar errores menores en limpieza
  }
}
cleanStaleTempFiles();

/**
 * Almacenamiento temporal en directorio local ./tmp.
 * El archivo se elimina automáticamente tras el análisis.
 */
const storage = multer.diskStorage({
  destination: (_req, _file, callback) => {
    cleanStaleTempFiles();
    callback(null, TEMP_DIR);
  },
  filename: (_req, file, callback) => {
    const uniqueSuffix = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    const ext = path.extname(file.originalname).toLowerCase();
    callback(null, `egg-video-${uniqueSuffix}${ext}`);
  },
});

/**
 * Instancia de Multer configurada para recibir un único archivo de video.
 */
const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: MAX_FILE_SIZE_BYTES,
    files: 1,
  },
});

/**
 * Middleware para subida de video en el campo "file".
 * Maneja errores de Multer y los convierte a respuestas HTTP estándar.
 */
function uploadVideoMiddleware(req, res, next) {
  const handler = upload.single('file');

  handler(req, res, (err) => {
    if (!err) return next();

    // Error de tamaño máximo superado
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({
        success: false,
        message: `El archivo supera el tamaño máximo permitido de ${MAX_FILE_SIZE_MB} MB.`,
      });
    }

    // Error de formato inválido (lanzado en fileFilter)
    if (err.status === 415) {
      return res.status(415).json({
        success: false,
        message: err.message,
      });
    }

    // Error de campo inesperado
    if (err.code === 'LIMIT_UNEXPECTED_FILE') {
      return res.status(400).json({
        success: false,
        message: 'Campo de archivo inesperado. Use el campo "file".',
      });
    }

    // Error genérico de Multer
    next(err);
  });
}

module.exports = { uploadVideoMiddleware };
