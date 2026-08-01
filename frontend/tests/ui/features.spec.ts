import { expect, test } from '@playwright/test';

test('quiz setup screen starts level 1 quiz', async ({ page }) => {
  await page.route('**/api/questions**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'math-1-1',
          subject: 'math',
          level: 1,
          question_text: 'セットアップ後の問題',
          options: ['1', '2', '3', '4'],
          correct_answer: '2',
          hint: 'ヒント',
          media: { image_url: null, audio_url: null },
        },
      ]),
    });
  });

  await page.goto('/quiz');
  await expect(page.getByRole('heading', { name: 'クイズを選ぼう' })).toBeVisible();
  await page.getByRole('button', { name: '🧮 算数' }).click();
  await page.getByRole('button', { name: '1', exact: true }).click();
  await page.getByRole('button', { name: /算数 レベル 1 をはじめる/ }).click();
  await expect(page).toHaveURL(/subject=math/);
  await expect(page).toHaveURL(/level=1/);
  await expect(page.getByText('セットアップ後の問題')).toBeVisible();
});

test('history shows summary and retry when logged-out CTA path', async ({ page }) => {
  await page.goto('/history');
  await expect(page.getByRole('heading', { name: '学習履歴' })).toBeVisible();
  await expect(page.getByText('学習履歴を見るにはログイン')).toBeVisible();
  await expect(page.getByRole('link', { name: 'ログインしてはじめる' })).toBeVisible();
});

test('connection test includes question bank stats row', async ({ page }) => {
  await page.route('**/api/health**', async (route) => {
    const url = route.request().url();
    if (url.includes('include_diagnostic')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          database_configured: true,
          database_ping_ok: true,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });
  await page.route('**/api/steps/today', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        authenticated: false,
        today_ymd: '2026-08-01',
        goal_steps: 5000,
        steps: null,
        source: 'none',
      }),
    });
  });
  await page.route('**/api/chat/capabilities', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ openai_configured: false, reply_mode: 'simple' }),
    });
  });
  await page.route('**/api/stats/summary**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        database_configured: true,
        timeline: [],
        quiz_sessions_week: 0,
        quiz_sessions_total: 0,
        average_score_week: 0,
        answers_count_week: 0,
        answer_accuracy_week: null,
        character: null,
        window_days: 7,
        weekly_activity: [],
        subject_breakdown: [],
        steps_goal: 5000,
        steps_today: null,
        steps_ymd: null,
        steps_source: null,
      }),
    });
  });
  await page.route('**/api/preprocess-image/info', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ algorithm: 'test', max_edge: 512 }),
    });
  });
  await page.route('**/api/questions/bank-stats**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        database_configured: true,
        total: 100,
        by_subject_level: [{ subject: 'math', level: 1, count: 5 }],
        gaps: [],
        recommended_min_per_level: 5,
        ready_for_quiz: true,
      }),
    });
  });

  await page.goto('/connection-test');
  await expect(
    page.getByText('GET /api/questions/bank-stats（問題バンク）'),
  ).toBeVisible();
  await expect(page.getByText(/"total": 100/)).toBeVisible({ timeout: 15_000 });
});

test('onboarding redirects guests to login', async ({ page }) => {
  await page.goto('/onboarding');
  await expect(page).toHaveURL(/\/login/);
});

test('parent dashboard shows weekly chart section labels', async ({ page }) => {
  await page.route('**/api/stats/summary**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        database_configured: true,
        window_days: 7,
        quiz_sessions_week: 2,
        quiz_sessions_total: 2,
        average_score_week: 80,
        answers_count_week: 10,
        answer_accuracy_week: 80,
        character: null,
        timeline: [],
        weekly_activity: [
          { date: '2026-07-30', quiz_sessions: 1, average_score: 80 },
          { date: '2026-07-31', quiz_sessions: 1, average_score: 80 },
        ],
        subject_breakdown: [
          {
            subject: 'math',
            sessions_week: 2,
            average_score_week: 80,
            answers_count_week: 10,
            answer_accuracy_week: 80,
          },
        ],
        steps_goal: 5000,
        steps_today: null,
        steps_ymd: null,
        steps_source: null,
      }),
    });
  });
  await page.route('**/api/steps/week**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        authenticated: false,
        today_ymd: '2026-08-01',
        goal_steps: 5000,
        source: 'none',
        days: [],
      }),
    });
  });

  await page.goto('/parent-dashboard');
  await expect(page.getByText('週間クイズ（直近7日）')).toBeVisible();
  await expect(page.getByText('教科別（今週）')).toBeVisible();
  await expect(page.getByText('算数', { exact: true })).toBeVisible();
});
