import { expect, test } from '@playwright/test';

test('quiz complete payload includes question_id', async ({ page }) => {
  await page.route('**/api/questions**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'math-1-001',
          subject: 'math',
          level: 1,
          question_text: '1 + 2 は？',
          options: ['3', '4', '5', '6'],
          correct_answer: '3',
          hint: '1 と 2 を足す',
          media: { image_url: null, audio_url: null },
        },
      ]),
    });
  });

  let capturedBody: unknown = null;
  await page.route('**/api/quiz/complete', async (route) => {
    capturedBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        score_percent: 100,
        correct: 1,
        total: 1,
        saved: false,
        details: [],
        gained_xp: 30,
      }),
    });
  });

  await page.goto('/quiz?subject=math&level=1');
  await page.getByRole('button', { name: '3' }).click();
  await page.getByRole('button', { name: '結果を見る' }).click();
  await expect(page.getByRole('heading', { name: 'クイズ完了！' })).toBeVisible();

  expect(capturedBody).not.toBeNull();
  const body = capturedBody as {
    answers?: Array<{ question_id?: string; question_index?: number }>;
  };
  expect(body.answers?.length).toBe(1);
  expect(body.answers?.[0]?.question_id).toBe('math-1-001');
  expect(body.answers?.[0]?.question_index).toBe(1);
});

test('parent dashboard renders stats summary values', async ({ page }) => {
  await page.route('**/api/stats/summary**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        database_configured: true,
        window_days: 7,
        quiz_sessions_week: 4,
        quiz_sessions_total: 21,
        average_score_week: 83.3,
        answers_count_week: 12,
        answer_accuracy_week: 75,
        character: {
          display_name: 'テストキャラ',
          experience: 230,
          level: 3,
          image_url: null,
        },
        timeline: [
          {
            created_at: '2026-05-11T10:00:00+00:00',
            subject: 'math',
            level: 2,
            score: 90,
            kind: 'quiz_session',
          },
        ],
        weekly_activity: [
          { date: '2026-05-11', quiz_sessions: 1, average_score: 90 },
        ],
        subject_breakdown: [
          {
            subject: 'math',
            sessions_week: 4,
            average_score_week: 83.3,
            answers_count_week: 12,
            answer_accuracy_week: 75,
          },
        ],
        steps_goal: 5000,
        steps_today: 3200,
        steps_ymd: '2026-05-11',
        steps_source: 'database',
      }),
    });
  });
  await page.route('**/api/steps/week**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        authenticated: false,
        today_ymd: '2026-05-11',
        goal_steps: 5000,
        source: 'none',
        days: [],
      }),
    });
  });

  await page.goto('/parent-dashboard');
  await expect(page.getByRole('heading', { name: '保護者ダッシュボード' })).toBeVisible();
  await expect(page.getByText('累計 21 セッション')).toBeVisible();
  await expect(page.getByText('ログインすると表示', { exact: true })).toBeVisible();
  await expect(page.getByText('保護者ダッシュボードはログイン後がおすすめ')).toBeVisible();
  await expect(page.getByText('算数 クイズ')).toBeVisible();
});

test('connection test shows extra API checks as OK', async ({ page }) => {
  await page.route('**/api/health?include_diagnostic=true', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        database_configured: true,
        database_ping_ok: true,
      }),
    });
  });
  await page.route('**/api/health', async (route) => {
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
        today_ymd: '2026-05-11',
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
      body: JSON.stringify({
        algorithm: 'binary_scribble_v3_famicom',
        max_edge: 512,
        description: 'test',
        tips: ['a', 'b'],
      }),
    });
  });

  await page.goto('/connection-test');
  await expect(page.getByRole('heading', { name: 'ユーザー接続テスト' })).toBeVisible();
  await expect(page.getByText('GET /api/steps/today（認証なし）')).toBeVisible();
  await expect(page.getByText('GET /api/chat/capabilities')).toBeVisible();
  await expect(page.getByText('GET /api/stats/summary（認証なし）')).toBeVisible();
  await expect(page.getByText('GET /api/preprocess-image/info')).toBeVisible();
  await expect(page.getByText('OK').first()).toBeVisible();
});

test('upload shows preprocess preview and quality hint', async ({ page }) => {
  test.setTimeout(180_000);
  await page.route('**/api/preprocess-image/info', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        algorithm: 'binary_scribble_v3_famicom',
        max_edge: 512,
        description: 'test',
        tips: ['a', 'b'],
      }),
    });
  });
  await page.route('**/api/preprocess-image', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        imageBase64:
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=',
        mime: 'image/png',
        algorithm: 'binary_scribble_v3_famicom',
        meta: {
          threshold: 120,
          inkRatio: 0.02,
          hasContent: true,
          contentWidth: 120,
          contentHeight: 80,
        },
      }),
    });
  });
  await page.route('**/api/generate-character', async (route) => {
    await new Promise((r) => setTimeout(r, 350));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        image: 'https://example.com/character.png',
      }),
    });
  });

  await page.goto('/', { waitUntil: 'load', timeout: 120_000 });
  await expect(page.getByRole('heading', { name: 'まなとも' })).toBeVisible({
    timeout: 120_000,
  });
  await page.getByRole('button', { name: '新しいキャラを作る' }).click();
  await expect(page).toHaveURL(/\/upload$/);
  await expect(page.getByRole('heading', { name: 'キャラクターを作ろう' })).toBeVisible({
    timeout: 120_000,
  });
  await page.locator('#file-upload').setInputFiles(
    {
      name: 'scribble.png',
      mimeType: 'image/png',
      buffer: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=',
        'base64',
      ),
    },
    { force: true },
  );
  await page.getByLabel('名前').fill('ぴょんた');
  await page.getByRole('button', { name: '✨ キャラクターを作る ✨' }).click();
  await expect(page.getByText('手書き検出プレビュー（線画抽出）')).toBeVisible();
  await expect(page.getByText(/線の濃さ:/)).toBeVisible();
  await expect(page.getByText(/線が少なめです/)).toBeVisible();
  await page.getByRole('button', { name: 'プレビューを拡大' }).click();
  await expect(page.getByRole('heading', { name: '前処理プレビュー（拡大）' })).toBeVisible();
  await expect(page.getByAltText('原画像プレビュー拡大')).toBeVisible();
  await expect(page.getByAltText('前処理プレビュー拡大')).toBeVisible();
});
