import { OpenRouter } from '@openrouter/sdk';
import {
  openrouterApiKey,
  openrouterModel,
  sttApiKey,
  sttApiUrl,
  sttModel,
} from '../config/env.js';

// Клиент OpenRouter создаём один раз на модуль
const openrouter =
  openrouterApiKey &&
  new OpenRouter({
    apiKey: openrouterApiKey,
  });

// userId -> true (режим чата с ИИ включён)
const aiChatUsers = new Map();

const getUserId = (ctx) =>
  ctx.user?.user_id ?? ctx.message?.body?.user?.user_id ?? null;

export const isAiChatActive = (ctx) => {
  const userId = getUserId(ctx);
  if (!userId) return false;
  return aiChatUsers.has(userId);
};

export const startAiChat = async (ctx) => {
  const userId = getUserId(ctx);
  if (!userId) {
    return ctx.reply('Не удалось определить пользователя для чата с ИИ.');
  }

  aiChatUsers.set(userId, true);

  return ctx.reply(
    [
      'Вы в режиме чата с ИИ 🤖.',
      'Вы можете отправить **текстовое сообщение** или **голосовое сообщение** с вопросом.',
      '',
      'Просто напишите вопрос или запишите голосом, и я постараюсь ответить максимально понятно.',
    ].join('\n')
  );
};

export const stopAiChat = (ctx) => {
  const userId = getUserId(ctx);
  if (!userId) return;
  aiChatUsers.delete(userId);
};

const callOpenRouter = async (text) => {
  if (!openrouterApiKey) {
    throw new Error(
      'OPENROUTER_API_KEY не задан. Добавьте его в переменные окружения.'
    );
  }

  if (!openrouter) {
    throw new Error('Клиент OpenRouter не инициализирован.');
  }

  const response = await openrouter.chat.send({
    httpReferer: 'https://max-bot.local',
    xTitle: 'Max Bot AI Chat',
    chatGenerationParams: {
      model: openrouterModel,
      // Нам не нужно стримить, достаточно обычного ответа
      messages: [
        {
          role: 'system',
          content:
            'Ты дружелюбный русскоязычный ассистент, который отвечает кратко и по делу.',
        },
        {
          role: 'user',
          content: text,
        },
      ],
      stream: false,
    },
  });

  const answer =
    response.choices?.[0]?.message?.content?.trim() ||
    'Не удалось получить ответ от модели.';

  return answer;
};

const extractAudioAttachment = (attachments) => {
  if (!Array.isArray(attachments)) return null;
  return (
    attachments.find((a) => a?.type === 'audio' || a?.type === 'voice') || null
  );
};

const extractAudioUrl = (attachment) => {
  if (!attachment) return null;
  return (
    attachment.url ||
    attachment.file_url ||
    attachment.fileUrl ||
    attachment.payload?.url ||
    attachment.payload?.file_url ||
    attachment.payload?.fileUrl ||
    null
  );
};

const transcribeAudio = async (audioUrl) => {
  if (!sttApiUrl) {
    throw new Error('STT_API_URL не настроен.');
  }

  const audioResponse = await fetch(audioUrl);
  if (!audioResponse.ok) {
    throw new Error(
      `Не удалось скачать аудио: ${audioResponse.status} ${audioResponse.statusText}`
    );
  }

  const audioBlob = await audioResponse.blob();

  const formData = new FormData();
  formData.append('file', audioBlob, 'voice.webm');

  const sttResponse = await fetch(sttApiUrl, {
    method: 'POST',
    body: formData,
  });

  if (!sttResponse.ok) {
    const errText = await sttResponse.text().catch(() => '');
    throw new Error(
      `Ошибка STT: ${sttResponse.status} ${sttResponse.statusText} ${errText}`
    );
  }

  const data = await sttResponse.json();
  const text = data?.text?.trim?.();
  if (!text) {
    throw new Error('STT не вернул текст.');
  }
  return text;
};

export const handleAiMessage = async (ctx) => {
  const body = ctx.message?.body ?? {};
  let text = body.text?.trim?.() || '';

  // Простейшее определение голосового сообщения: наличие аудио/голосового вложения
  const attachments = body.attachments || [];
  const audioAttachment = extractAudioAttachment(attachments);
  const hasAudioAttachment = Boolean(audioAttachment);

  if (!text && !hasAudioAttachment) {
    return ctx.reply(
      'Для чата с ИИ отправьте, пожалуйста, текстовое сообщение или голосовое с вопросом.'
    );
  }

  try {
    if (hasAudioAttachment && !text) {
      const url = extractAudioUrl(audioAttachment);
      if (!url) {
        return ctx.reply(
          'Не удалось получить ссылку на голосовое сообщение. Попробуйте еще раз или отправьте вопрос текстом.'
        );
      }

      await ctx.reply('Преобразую голос в текст…');
      text = await transcribeAudio(url);
    }

    await ctx.reply('Думаю над ответом…');
    const answer = await callOpenRouter(text);
    return ctx.reply(answer);
  } catch (error) {
    console.error('Ошибка при обращении к OpenRouter:', error);
    return ctx.reply(
      'Не удалось получить ответ от ИИ. Попробуйте позже или напишите вопрос иначе.'
    );
  }
};

