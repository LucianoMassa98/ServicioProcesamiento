'use strict';

const { Sequelize } = require('sequelize');

// ─── Validación de variable de entorno ────────────────────────────────────────
if (!process.env.DATABASE_URL) {
  throw new Error('[Config] La variable de entorno DATABASE_URL es obligatoria.');
}

// ─── Instancia Sequelize con URL única ────────────────────────────────────────
const sequelize = new Sequelize(process.env.DATABASE_URL, {
  dialect: 'postgres',
  logging: process.env.NODE_ENV === 'development' ? console.log : false,
  dialectOptions: {
    // Habilitar SSL en producción si el proveedor lo requiere
    ssl:
      process.env.NODE_ENV === 'production'
        ? { require: true, rejectUnauthorized: false }
        : false,
  },
  pool: {
    max: 10,
    min: 0,
    acquire: 30000,
    idle: 10000,
  },
});

module.exports = { sequelize };
