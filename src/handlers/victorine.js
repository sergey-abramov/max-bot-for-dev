import { Keyboard } from '@maxhub/max-bot-api';

const questions = [
  {
    question: 'Что такое ООП?',
    options: [
      'Объектно-ориентированное программирование — методология программирования, основанная на представлении программы в виде совокупности объектов, каждый из которых является экземпляром определенного класса, а классы образуют иерархию наследования.',
      'Объектно-ориентированное программирование — так называют любой тип программирования, в котором используются понятия высокого уровня и, в отличие от Assembler, в котором не работают напрямую с ячейками памяти ПК.',
      'Объектно-ориентированное программирование — просто красивое понятие. Если вдуматься, оно не несет дополнительной смысловой нагрузки, просто программисты любят аббревиатуры, так области их знаний выглядят сложнее.',
      'Очень одинокий программист.',
    ],
    correct: 1,
  },
  {
    question: 'Что такое класс в Java?',
    options: [
      'Уровень сложности программы. Все операторы делятся на классы в зависимости от сложности их использования.',
      'Базовый элемент объектно-ориентирован­ного программирования в языке Java.',
      'Просто одно из возможных названий переменной.',
      'Такое понятие есть только в C++, в Java такого понятия нет.',
    ],
    correct: 2,
  },
  {
    question: 'Как объявить класс в коде?',
    options: [
      'class MyClass {}',
      'new class MyClass {}',
      'select * from class MyClass {}',
      'MyClass extends class {}',
    ],
    correct: 1,
  },
];

// userId -> { index, correct }
const activeQuizzes = new Map();

const getUserId = (ctx) => ctx.user?.user_id ?? ctx.message?.body?.user?.user_id;

const buildQuestionText = (q, index) => {
  const header = `Вопрос ${index + 1} из ${questions.length}\n${q.question}\n`;
  const options = q.options
    .map((opt, i) => `${i + 1}. ${opt}`)
    .join('\n\n');
  return `${header}\n${options}`;
};

const buildKeyboard = (questionIndex) => {
  const payloadPrefix = `victorine:${questionIndex}:`;
  const row = [
    Keyboard.button.callback('1', `${payloadPrefix}1`),
    Keyboard.button.callback('2', `${payloadPrefix}2`),
    Keyboard.button.callback('3', `${payloadPrefix}3`),
    Keyboard.button.callback('4', `${payloadPrefix}4`),
  ];

  return Keyboard.inlineKeyboard([row]);
};

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

    activeQuizzes.set(userId, {
      index: 0,
      correct: 0,
    });

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

    await ctx.reply('Запускаем викторину по Java! 🚀\nВо время викторины используйте только кнопки ниже.');
    const first = questions[0];
    return ctx.reply(buildQuestionText(first, 0), {
      attachments: [buildKeyboard(0)],
    });
  } catch (error) {
    console.error('Ошибка при запуске викторины:', error);
    return ctx.reply('Произошла ошибка при запуске викторины. Попробуйте позже.');
  }
};

export const handleVictorineAnswer = async (ctx) => {
  try {
    const userId = getUserId(ctx);
    if (!userId) return;

    const state = activeQuizzes.get(userId);
    if (!state) return;

    const callback = ctx.callback;
    const payload = callback?.payload;

    if (!payload || !payload.startsWith('victorine:')) {
      // Сообщения/коллбеки не по теме викторины во время её прохождения
      return ctx.reply('Сейчас идёт викторина. Пожалуйста, отвечайте, используя кнопки с вариантами ответов.');
    }

    const [, qIndexStr, answerStr] = payload.split(':');
    const payloadQuestionIndex = Number.parseInt(qIndexStr, 10);
    const answer = Number.parseInt(answerStr, 10);

    if (
      !Number.isInteger(payloadQuestionIndex) ||
      payloadQuestionIndex !== state.index ||
      !Number.isInteger(answer) ||
      answer < 1 ||
      answer > 4
    ) {
      return ctx.reply('Некорректный ответ. Пожалуйста, используйте кнопки под сообщением.');
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

    const currentQuestion = questions[state.index];
    if (answer === currentQuestion.correct) {
      state.correct += 1;
      await ctx.reply('Верно ✅');
    } else {
      await ctx.reply('Неверно ❌');
    }

    state.index += 1;

    if (state.index >= questions.length) {
      await ctx.reply(
        `Тест завершён! Ваш результат: ${state.correct} из ${questions.length} правильных ответов.`
      );
      activeQuizzes.delete(userId);

      // Возвращаем пользователя в главное меню выбора действий
      await ctx.reply('Выберите дальнейшее действие:', {
        attachments: [
          Keyboard.inlineKeyboard([
            [
              Keyboard.button.callback('ℹ️ Информация обо мне', 'menu:hello'),
              Keyboard.button.callback('📝 Викторина по Java', 'menu:victorine'),
            ],
          ]),
        ],
      });

      return;
    }

    const nextQuestion = questions[state.index];
    return ctx.reply(buildQuestionText(nextQuestion, state.index), {
      attachments: [buildKeyboard(state.index)],
    });
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

