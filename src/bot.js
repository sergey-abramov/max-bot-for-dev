import { Bot, Keyboard } from '@maxhub/max-bot-api';
import {
  handleVictorineAnswer,
  isVictorineActive,
  startVictorine,
} from './handlers/victorine.js';
import {
  handleAiMessage,
  isAiChatActive,
  startAiChat,
  stopAiChat,
} from './handlers/aiChat.js';

// Создайте экземпляр класса Bot и передайте ему токен 
const bot = new Bot(process.env.BOT_TOKEN);

// Добавьте слушатели обновлений
// MAX Bot API будет вызывать их, когда пользователи взаимодействуют с ботом

// Устанавливает список команд, который пользователь будет видеть в чате с ботом
bot.api.setMyCommands([
  {
    name: 'start',
    description: 'Запустить бота',
  },
]);

const getSafeUser = (ctx) => ctx.user ?? ctx.message?.body?.user ?? null;

const logUserAction = (ctx, action, extra = {}) => {
  const user = getSafeUser(ctx);
  const chat = ctx.chat;

  console.log('[USER_ACTION]', {
    timestamp: new Date().toISOString(),
    action,
    user: user && {
      id: user.user_id,
      name: user.name,
      username: user.username,
      role: user.role,
    },
    chat: chat && {
      id: chat.chat_id,
      type: chat.type,
      title: chat.title,
    },
    updateType: ctx.updateType,
    extra,
  });
};

// Обработчик для команды '/start'
bot.command('start', async (ctx) => {
  try {
    logUserAction(ctx, 'start_command');

    await ctx.reply('Добро пожаловать! Выберите действие:', {
      attachments: [
        Keyboard.inlineKeyboard([
          [
            Keyboard.button.callback('ℹ️ Информация обо мне', 'menu:hello'),
            Keyboard.button.callback('📝 Викторина по Java', 'menu:victorine'),
          ],
          [
            Keyboard.button.callback('🤖 Чат с ИИ', 'menu:chat_ai'),
          ],
        ]),
      ],
    });
  } catch (error) {
    console.error('Ошибка в обработчике /start:', error);
    return ctx.reply('Произошла ошибка при выполнении команды /start. Попробуйте позже.');
  }
});

// Кнопка "Информация о пользователе"
bot.action('menu:hello', async (ctx) => {
  try {
    logUserAction(ctx, 'menu_hello');

    const user = getSafeUser(ctx);
    if (!user) {
      return ctx.reply('Не удалось определить информацию о пользователе.');
    }

    const infoLines = [
      'Информация о вас:',
      `ID: ${user.user_id}`,
      `Имя: ${user.name ?? 'неизвестно'}`,
      `Username: ${user.username ?? 'не задан'}`,
      `Роль: ${user.role ?? 'неизвестно'}`,
    ];

    return ctx.reply(infoLines.join('\n'));
  } catch (error) {
    console.error('Ошибка в обработчике menu:hello:', error);
    return ctx.reply('Произошла ошибка при получении информации о пользователе.');
  }
});

// Кнопка "Викторина по Java"
bot.action('menu:victorine', async (ctx) => {
  try {
    logUserAction(ctx, 'menu_victorine');
    stopAiChat(ctx);
    return startVictorine(ctx);
  } catch (error) {
    console.error('Ошибка в обработчике menu:victorine:', error);
    return ctx.reply('Не удалось запустить викторину. Попробуйте позже.');
  }
});

// Кнопка "Чат с ИИ"
bot.action('menu:chat_ai', async (ctx) => {
  try {
    logUserAction(ctx, 'menu_chat_ai');
    // Выключаем викторину, если она вдруг активна
    if (isVictorineActive(ctx)) {
      await ctx.reply(
        'Викторина завершена. Переходим в режим чата с ИИ.'
      );
    }
    stopAiChat(ctx);
    return startAiChat(ctx);
  } catch (error) {
    console.error('Ошибка в обработчике menu:chat_ai:', error);
    return ctx.reply('Не удалось запустить чат с ИИ. Попробуйте позже.');
  }
});

// Обработчик нажатий на кнопки викторины
bot.action(/victorine:.*/, (ctx) => handleVictorineAnswer(ctx));

// Обработчик для любого другого сообщения
bot.on('message_created', (ctx) => {
  try {
    const text = ctx.message?.body?.text ?? '';

    // Игнорируем команды, их обрабатывают хэндлеры bot.command
    if (typeof text === 'string' && text.startsWith('/')) {
      // При любой новой команде выходим из режима чата с ИИ
      stopAiChat(ctx);

      if (isVictorineActive(ctx)) {
        return ctx.reply(
          'Сейчас идёт викторина. Дождитесь окончания или отвечайте с помощью кнопок под вопросом.'
        );
      }
      return;
    }

    if (isVictorineActive(ctx)) {
      // Любые текстовые сообщения во время викторины считаем "не по теме"
      return ctx.reply(
        'Сейчас идёт викторина. Пожалуйста, используйте кнопки под сообщением для ответа.'
      );
    }

    if (isAiChatActive(ctx)) {
      return handleAiMessage(ctx);
    }

    return ctx.reply(
      'Вы можете открыть /start и выбрать, например, "Чат с ИИ", чтобы задать вопрос.'
    );
  } catch (error) {
    console.error('Ошибка в обработчике message_created:', error);
    return ctx.reply('Произошла внутренняя ошибка. Попробуйте позже.');
  }
});

// Глобальная обработка необработанных ошибок бота
bot.catch(async (err, ctx) => {
  console.error('[BOT_UNHANDLED_ERROR]', {
    timestamp: new Date().toISOString(),
    error: {
      message: err?.message,
      stack: err?.stack,
      name: err?.name,
    },
    update: ctx?.update,
  });

  try {
    if (ctx) {
      await ctx.reply('Произошла непредвиденная ошибка. Попробуйте позже.');
    }
  } catch {
    // игнорируем ошибки при отправке сообщения об ошибке
  }
});

export default bot;