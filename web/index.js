import bot from './bot.js'

const resolvedMode = (process.env.MAX_BOT_MODE ?? 'webhook').trim().toLowerCase();
const isProduction = (process.env.NODE_ENV ?? '').trim().toLowerCase() === 'production'
  || (process.env.VERCEL_ENV ?? '').trim().toLowerCase() === 'production';

if (resolvedMode === 'polling' && !isProduction) {
  bot.start();
  console.log('Бот запущен в polling-режиме (dev only).');
} else {
  if (resolvedMode === 'polling' && isProduction) {
    throw new Error('MAX_BOT_MODE=polling запрещен в production. Используйте webhook-режим.');
  }
  console.log('Polling runtime отключен. Используется webhook-режим.');
}