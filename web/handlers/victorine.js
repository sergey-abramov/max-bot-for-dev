import { Keyboard } from '@maxhub/max-bot-api';

const QUIZ_API_URL = process.env.QUIZ_API_URL || 'http://localhost:8001';
const QUIZ_QUESTIONS_PER_SESSION = 3;

// userId -> { topicSlug, topicTitle, currentQuestionId, correct, total }
const activeQuizzes = new Map();

const getUser = (ctx) => ctx.user ?? ctx.message?.body?.user ?? null;

const getUserId = (ctx) => getUser(ctx)?.user_id;

const fetchJson = async (url, options) => {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options && options.headers),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed: ${response.status} ${text}`);
  }

  return response.json();
};

const syncUserWithQuizDb = async (ctx) => {
  const user = getUser(ctx);
  if (!user) return;

  try {
    const response = await fetch(`${QUIZ_API_URL}/users/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        telegram_id: user.user_id,
        username: user.username ?? null,
        first_name: user.name ?? null,
        last_name: null,
      }),
    });

    if (!response.ok) {
      console.error(
        '[QUIZ_DB_SYNC_ERROR]',
        'Unexpected status',
        response.status,
        await response.text()
      );
    }
  } catch (error) {
    console.error('[QUIZ_DB_SYNC_ERROR]', error);
  }
};

const buildQuestionText = (question, index, totalPlanned) => {
  const header = `Вопрос ${index + 1} из ${totalPlanned}\n${question.text}\n`;

  const options = Object.entries(question.options || {})
    .sort(([a], [b]) => a.localeCompare(b, 'ru'))
    .map(([key, text]) => `${key}. ${text}`)
    .join('\n\n');

  return `${header}\n${options}`;
};

const buildAnswerKeyboard = (topicSlug, questionId, options) => {
  const payloadPrefix = `victorine:answer:${topicSlug}:${questionId}:`;

  const keys = Object.keys(options || {}).sort((a, b) => a.localeCompare(b, 'ru'));
  const buttons = keys.map((key) =>
    Keyboard.button.callback(key, `${payloadPrefix}${key}`)
  );

  return Keyboard.inlineKeyboard([buttons]);
};

const buildTopicsKeyboard = (topics) =>
  Keyboard.inlineKeyboard(
    topics.map((topic) => [
      Keyboard.button.callback(topic.title, `victorine:topic:${topic.slug}`),
    ])
  );

const loadTopics = async () => {
  const topics = await fetchJson(`${QUIZ_API_URL}/topics`);
  return topics;
};

const loadRandomQuestionForTopic = async (topicSlug) =>
  fetchJson(`${QUIZ_API_URL}/topics/${encodeURIComponent(topicSlug)}/random-question`);

export const isVictorineActive = (ctx) => {
  const userId = getUserId(ctx);
  if (!userId) return false;
  return activeQuizzes.has(userId);
};

export const startVictorine = async (ctx) => {
  try {
    const userId = getUserId(ctx);
    if (!userId) {
      return ctx.reply('Не удалось определить пользователя для викторины.');
    }

    await syncUserWithQuizDb(ctx);

    const topics = await loadTopics();
    if (!Array.isArray(topics) || topics.length === 0) {
      return ctx.reply('Сейчас нет доступных тем викторины. Попробуйте позже.');
    }

    const keyboard = buildTopicsKeyboard(topics);

    const user = ctx.user ?? ctx.message?.body?.user;
    console.log('[VICTORINE_START]', {
      timestamp: new Date().toISOString(),
      user: user && {
        id: user.user_id,
        name: user.name,
        username: user.username,
        role: user.role,
      },
    });

    await ctx.reply(
      'Запускаем викторину! 🚀\nВыберите тему, по которой хотите пройти тест:',
      {
        attachments: [keyboard],
      }
    );
    return;
  } catch (error) {
    console.error('Ошибка при запуске викторины:', error);
    return ctx.reply('Произошла ошибка при запуске викторины. Попробуйте позже.');
  }
};

export const handleVictorineAnswer = async (ctx) => {
  try {
    const userId = getUserId(ctx);
    if (!userId) return;

    const callback = ctx.callback;
    const payload = callback?.payload;

    if (!payload || !payload.startsWith('victorine:')) {
      // Сообщения/коллбеки не по теме викторины во время её прохождения
      return ctx.reply('Сейчас идёт викторина. Пожалуйста, отвечайте, используя кнопки с вариантами ответов.');
    }

    const [, kind, ...rest] = payload.split(':');

    if (kind === 'topic') {
      const [topicSlug] = rest;
      if (!topicSlug) {
        return ctx.reply('Не удалось определить выбранную тему. Попробуйте ещё раз.');
      }

      const topics = await loadTopics();
      const topic = topics.find((t) => t.slug === topicSlug);
      if (!topic) {
        return ctx.reply('Выбранная тема больше недоступна. Попробуйте выбрать другую.');
      }

      const question = await loadRandomQuestionForTopic(topicSlug);

      activeQuizzes.set(userId, {
        topicSlug,
        topicTitle: topic.title,
        currentQuestionId: question.id,
        correct: 0,
        total: 0,
      });

      const text = buildQuestionText(
        question,
        0,
        QUIZ_QUESTIONS_PER_SESSION
      );

      return ctx.reply(text, {
        attachments: [buildAnswerKeyboard(topicSlug, question.id, question.options)],
      });
    }

    if (kind !== 'answer') {
      return;
    }

    const state = activeQuizzes.get(userId);
    if (!state) {
      return ctx.reply('Викторина для вас не найдена. Попробуйте запустить её заново.');
    }

    const [topicSlug, questionIdStr, selectedKey] = rest;
    const questionId = Number.parseInt(questionIdStr, 10);

    if (!topicSlug || !Number.isInteger(questionId) || !selectedKey) {
      return ctx.reply('Некорректный ответ. Пожалуйста, используйте кнопки под сообщением.');
    }

    if (
      state.topicSlug !== topicSlug ||
      state.currentQuestionId !== questionId
    ) {
      return ctx.reply('Этот вопрос уже не актуален. Дождитесь следующего вопроса викторины.');
    }

    const user = ctx.user ?? ctx.message?.body?.user;
    console.log('[VICTORINE_ANSWER]', {
      timestamp: new Date().toISOString(),
      user: user && {
        id: user.user_id,
        name: user.name,
        username: user.username,
        role: user.role,
      },
      payload,
      state,
    });

    try {
      const apiUser = getUser(ctx);

      const result = await fetchJson(`${QUIZ_API_URL}/answers/submit`, {
        method: 'POST',
        body: JSON.stringify({
          telegram_id: apiUser?.user_id,
          username: apiUser?.username ?? null,
          first_name: apiUser?.name ?? null,
          last_name: null,
          question_id: questionId,
          selected_key: selectedKey,
        }),
      });

      if (result.is_correct) {
        state.correct += 1;
        await ctx.reply('Верно ✅');
      } else {
        await ctx.reply('Неверно ❌');
        if (result.correct_key) {
          await ctx.reply(`Правильный ответ: ${result.correct_key}`);
        }
      }

      state.total += 1;

      if (state.total >= QUIZ_QUESTIONS_PER_SESSION) {
        const stats = result.topic_stats;

        let summary = `Тест по теме «${state.topicTitle}» завершён! Ваш результат: ${state.correct} из ${state.total} правильных ответов.`;

        if (stats) {
          summary += `\n\nВсего по этой теме:\n- Правильных ответов: ${stats.correct_count}\n- Неправильных ответов: ${stats.wrong_count}\n- Всего ответов: ${stats.total_answers}`;
        }

        await ctx.reply(summary);
        activeQuizzes.delete(userId);

        await ctx.reply('Выберите дальнейшее действие:', {
          attachments: [
            Keyboard.inlineKeyboard([
              [
                Keyboard.button.callback('ℹ️ Информация обо мне', 'menu:hello'),
                Keyboard.button.callback('📝 Викторина', 'menu:victorine'),
              ],
            ]),
          ],
        });

        return;
      }

      const nextQuestion = await loadRandomQuestionForTopic(state.topicSlug);
      state.currentQuestionId = nextQuestion.id;

      const text = buildQuestionText(
        nextQuestion,
        state.total,
        QUIZ_QUESTIONS_PER_SESSION
      );

      return ctx.reply(text, {
        attachments: [
          buildAnswerKeyboard(
            state.topicSlug,
            nextQuestion.id,
            nextQuestion.options
          ),
        ],
      });
    } catch (apiError) {
      console.error('[QUIZ_API_ERROR]', apiError);
      await ctx.reply(
        'Не удалось связаться с сервисом викторины. Викторина завершена, попробуйте позже.'
      );
      activeQuizzes.delete(userId);

      await ctx.reply('Выберите дальнейшее действие:', {
        attachments: [
          Keyboard.inlineKeyboard([
            [
              Keyboard.button.callback('ℹ️ Информация обо мне', 'menu:hello'),
              Keyboard.button.callback('📝 Викторина', 'menu:victorine'),
            ],
          ]),
        ],
      });
      return;
    }
  } catch (error) {
    console.error('Ошибка при обработке ответа викторины:', error);
    try {
      await ctx.reply('Произошла ошибка при обработке ответа. Викторина завершена.');
    } catch {
      // игнорируем вторичную ошибку
    }
    const userId = getUserId(ctx);
    if (userId) {
      activeQuizzes.delete(userId);
    }
  }
};

