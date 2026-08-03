'use strict';

const { spawn, spawnSync } = require('child_process');
const path                 = require('path');

/**
 * EggCounterService
 *
 * Responsabilidad única: contar huevos en un video dado su ruta.
 *
 * IMPLEMENTACIÓN ACTUAL: OpenCV (Python) via child_process.
 *   - Detecta huevos marrones por color HSV + Watershed para grupos.
 *   - Rastrea centroides frame a frame.
 *   - Cuenta cada huevo la primera vez que cruza la línea horizontal.
 *
 * Para migrar a YOLO en el futuro, solo hace falta:
 *   1. Cambiar PYTHON_SCRIPT_PATH por el nuevo script.
 *   2. O crear una subclase que sobreescriba countEggs().
 *   VideoAnalysisService NO necesita cambios (DIP).
 *
 * Interfaz pública:
 *   countEggs(videoPath: string): Promise<{ eggs, processedFrames, processingTime }>
 */
class EggCounterService {
  /**
   * Ruta al script Python de conteo.
   * Relativa a la raíz del proyecto (process.cwd()).
   */
  static PYTHON_SCRIPT_PATH = path.join(
    path.resolve(__dirname, '../../'),
    'scripts',
    'egg_count.py',
  );

  /**
   * Control de concurrencia: límite de análisis en paralelo para evitar sobrecarga de RAM/CPU.
   * Por defecto 1 análisis a la vez (modificable por variable de entorno MAX_CONCURRENT_ANALYSES).
   */
  static MAX_CONCURRENCY = parseInt(process.env.MAX_CONCURRENT_ANALYSES || '1', 10);
  static activeCount = 0;
  static queue = [];

  /**
   * Procesa la cola de solicitudes pendientes respetando el límite de concurrencia.
   * @private
   */
  static _processQueue() {
    while (EggCounterService.activeCount < EggCounterService.MAX_CONCURRENCY && EggCounterService.queue.length > 0) {
      const task = EggCounterService.queue.shift();
      EggCounterService.activeCount++;

      console.log(
        `[EggCounterService] Procesando tarea de la cola (activas=${EggCounterService.activeCount}, en espera=${EggCounterService.queue.length})`
      );

      task.execute().finally(() => {
        EggCounterService.activeCount--;
        EggCounterService._processQueue();
      });
    }
  }

  /**
   * Resuelve el binario de Python disponible en el entorno.
   * Prioridad: PYTHON_BIN env var → python3 → python
   *
   * @returns {string} Nombre del ejecutable de Python.
   */
  static resolvePythonBin() {
    // Si el usuario configuró explícitamente la variable, respetarla.
    if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN;

    // Detectar automáticamente cuál está disponible en el PATH.
    for (const candidate of ['python3', 'python']) {
      const result = spawnSync(candidate, ['--version'], { encoding: 'utf8' });
      if (result.status === 0) return candidate;
    }

    // Último recurso: asumir python3 (el error será descriptivo).
    return 'python3';
  }

  /**
   * Cuenta los huevos que cruzan la línea de conteo en el video.
   * Encola la ejecución para evitar fallos de memoria RAM por múltiples procesos simultáneos.
   *
   * @param {string} videoPath - Ruta absoluta al archivo de video temporal.
   * @returns {Promise<{ eggs: number, processedFrames: number, processingTime: number }>}
   */
  async countEggs(videoPath) {
    return new Promise((resolve, reject) => {
      const task = {
        execute: () => this._runPythonCount(videoPath).then(resolve, reject),
      };

      EggCounterService.queue.push(task);
      EggCounterService._processQueue();
    });
  }

  /**
   * Ejecuta el script Python en un subproceso.
   *
   * @private
   * @param {string} videoPath
   * @returns {Promise<{ eggs: number, processedFrames: number, processingTime: number }>}
   */
  async _runPythonCount(videoPath) {
    return new Promise((resolve, reject) => {
      const pythonBin = EggCounterService.resolvePythonBin();

      const scriptArgs = [
        EggCounterService.PYTHON_SCRIPT_PATH,
        videoPath,
        '--line-ratio',       process.env.EGG_COUNTING_LINE_RATIO    || '0.50',
        '--min-area',         process.env.EGG_MIN_AREA                || '150',
        '--max-area',         process.env.EGG_MAX_AREA                || '12000',
        '--skip-frames',      process.env.EGG_PROCESS_EVERY_N_FRAMES  || '2',
        '--max-dist',         process.env.EGG_MAX_CENTROID_DIST       || '45',
        '--min-track-frames', process.env.EGG_MIN_TRACK_FRAMES        || '1',
        '--max-lost-frames',  process.env.EGG_MAX_LOST_FRAMES         || '6',
        '--warmup-frames',    process.env.EGG_WARMUP_FRAMES           || '60',
        '--peak-window',      process.env.EGG_PEAK_WINDOW             || '19',
        '--min-peak-dist',    process.env.EGG_MIN_PEAK_DIST           || '9.5',
        '--roi-ratio',        process.env.EGG_ROI_WIDTH_RATIO         || '0.78',
      ];

      console.log(`[EggCounterService] Iniciando: ${pythonBin} ${scriptArgs.join(' ')}`);

      const proc = spawn(pythonBin, scriptArgs);

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
      proc.stderr.on('data', (chunk) => { stderr += chunk.toString(); });

      proc.on('close', (code, signal) => {
        if (stderr.trim()) {
          console.log(`[EggCounterService] Script stderr:\n${stderr.trim()}`);
        }

        if (code !== 0) {
          const detail = code === null
            ? `fue terminado por señal ${signal} (posible falta de memoria RAM / OOM Killer en Docker/Railway)`
            : `terminó con código ${code}`;

          return reject(
            new Error(`egg_count.py ${detail}. Detalle: ${stderr.trim() || stdout.trim() || '(vacío)'}`),
          );
        }

        let result;
        try {
          result = JSON.parse(stdout.trim());
        } catch {
          return reject(
            new Error(`No se pudo parsear la salida del script: "${stdout.trim()}"`),
          );
        }

        if (result.error) {
          return reject(new Error(result.error));
        }

        console.log(
          `[EggCounterService] Resultado: eggs=${result.eggs} ` +
          `frames=${result.processedFrames} time=${result.processingTime}s`,
        );

        resolve({
          eggs:           result.eggs,
          processedFrames: result.processedFrames,
          processingTime:  result.processingTime,
        });
      });

      proc.on('error', (err) => {
        reject(
          new Error(
            `No se pudo iniciar "${pythonBin}". ` +
            `¿Está Python instalado y en el PATH? Detalle: ${err.message}`,
          ),
        );
      });
    });
  }
}

module.exports = EggCounterService;
