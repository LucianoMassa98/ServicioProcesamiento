# ServicioProcesamiento

API REST para analizar videos de cintas transportadoras de huevos.
Recibe un video, cuenta los huevos que cruzan una línea de conteo y devuelve el resultado.
El video **nunca se almacena**: solo se guarda temporalmente durante el análisis y se elimina automáticamente al finalizar.

---

## Tecnologías

- **Node.js** (≥ 18)
- **Express**
- **PostgreSQL** + **Sequelize ORM**
- **Multer** (manejo de archivos)
- **express-validator** (validaciones)
- Arquitectura **Clean Architecture**

---

## Estructura del proyecto

```
src/
├── index.js                        # Entry point
├── app.js                          # Configuración Express
├── config/
│   └── database.js                 # Conexión Sequelize (DATABASE_URL)
├── controllers/
│   └── video.controller.js
├── middlewares/
│   ├── upload.middleware.js        # Multer + validación formato/tamaño
│   └── error.middleware.js        # Manejador global de errores
├── models/
│   └── video-analysis.model.js
├── routes/
│   └── video.routes.js
└── services/
    ├── video-analysis.service.js  # Orquestador
    └── egg-counter.service.js     # Algoritmo de conteo (stub → YOLO)
```

---

## Configuración

Copiar `.env.example` a `.env` y completar los valores:

```bash
cp .env.example .env
```

| Variable            | Descripción                                      | Ejemplo                                         |
|---------------------|--------------------------------------------------|-------------------------------------------------|
| `PORT`              | Puerto del servidor                              | `3000`                                          |
| `NODE_ENV`          | Entorno (`development` / `production`)           | `development`                                   |
| `DATABASE_URL`      | URL de conexión PostgreSQL                       | `postgresql://user:pass@host:5432/db`           |
| `MAX_FILE_SIZE_MB`  | Tamaño máximo del video en MB (default: `500`)   | `500`                                           |

---

## Instalación y arranque

```bash
npm install
npm run dev        # Desarrollo (nodemon)
npm start          # Producción
```

---

## Endpoint

### `POST /api/videos/analyze`

**Content-Type:** `multipart/form-data`

| Campo      | Tipo   | Obligatorio | Descripción                        |
|------------|--------|-------------|------------------------------------|
| `file`     | File   | ✅           | Video (mp4, mov, avi, mkv)        |
| `name`     | String | ✅           | Nombre descriptivo del análisis    |
| `galponId` | UUID   | ✅           | UUID del galpón                    |

#### Respuesta exitosa `200`

```json
{
  "success": true,
  "message": "Video analizado correctamente.",
  "data": {
    "galponId": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Turno mañana - Galpón A",
    "eggs": 1524,
    "processedFrames": 9812,
    "processingTime": 10.48
  }
}
```

#### Errores

| Código | Descripción                            |
|--------|----------------------------------------|
| `400`  | Campos obligatorios faltantes o inválidos |
| `413`  | Archivo supera el tamaño máximo        |
| `415`  | Formato de video no soportado          |
| `500`  | Error interno del servidor             |

---

## Base de datos

Tabla: `video_analysis`

| Columna           | Tipo      | Descripción                          |
|-------------------|-----------|--------------------------------------|
| `id`              | UUID (PK) | Identificador único                  |
| `galpon_id`       | UUID      | Galpón asociado                      |
| `name`            | VARCHAR   | Nombre del análisis                  |
| `eggs`            | INTEGER   | Total de huevos contados             |
| `processed_frames`| INTEGER   | Fotogramas procesados                |
| `processing_time` | FLOAT     | Tiempo de procesamiento (segundos)   |
| `status`          | ENUM      | `pending/processing/completed/failed`|
| `created_at`      | TIMESTAMP | Fecha de creación                    |
| `updated_at`      | TIMESTAMP | Fecha de actualización               |

> ⚠️ La tabla **NO almacena** la ruta ni el contenido del video.

---

## Reemplazar EggCounterService por YOLO

Para integrar un modelo YOLO, modificar únicamente `src/services/egg-counter.service.js`.
La interfaz requerida es:

```js
async countEggs(videoPath: string): Promise<{
  eggs: number,
  processedFrames: number,
  processingTime: number
}>
```

`VideoAnalysisService` **no requiere cambios**.
