import dotenv from 'dotenv';
dotenv.config();

export const botToken = process.env.BOT_TOKEN;
export const port = process.env.PORT || 3000;
export const env = process.env.NODE_ENV;

// Подключение к базе данных (PostgreSQL)
export const databaseUrl = process.env.DATABASE_URL;

export const openrouterApiKey = process.env.OPENROUTER_API_KEY;
export const openrouterModel =
  process.env.OPENROUTER_MODEL || 'qwen/qwen-2.5-7b-instruct';

// Настройки для распознавания речи (STT)
// По умолчанию ориентируемся на OpenAI Whisper-совместимый API
export const sttApiKey = process.env.STT_API_KEY || process.env.OPENAI_API_KEY;
export const sttApiUrl =
  process.env.STT_API_URL || 'http://localhost:8000/transcribe';
export const sttModel = process.env.STT_MODEL || 'small';