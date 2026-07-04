import { expect, test } from '@playwright/test';

test('home renders and navigates to connection test', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'まなとも' })).toBeVisible();
  await page.getByRole('link', { name: '接続テスト' }).click();
  await expect(page.getByRole('heading', { name: 'ユーザー接続テスト' })).toBeVisible();
});

test('quiz flow finishes with mocked APIs', async ({ page }) => {
  await page.route('**/api/questions**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'math-1-1',
          subject: 'math',
          level: 1,
          question_text: '1 + 1 は？',
          options: ['2', '3', '4', '5'],
          correct_answer: '2',
          hint: '1 と 1 を足すよ',
          media: { image_url: null, audio_url: null },
        },
        {
          id: 'math-1-2',
          subject: 'math',
          level: 1,
          question_text: '2 + 1 は？',
          options: ['1', '2', '3', '4'],
          correct_answer: '3',
          hint: '2 と 1 を足すよ',
          media: { image_url: null, audio_url: null },
        },
      ]),
    });
  });

  await page.route('**/api/quiz/complete', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        score_percent: 100,
        correct: 2,
        total: 2,
        saved: false,
        details: [],
      }),
    });
  });

  await page.goto('/quiz?subject=math&level=1');
  await expect(page.getByText('1 + 1 は？')).toBeVisible();
  await page.getByRole('button', { name: '2' }).click();
  await page.getByRole('button', { name: '次の問題へ' }).click();

  await expect(page.getByText('2 + 1 は？')).toBeVisible();
  await page.getByRole('button', { name: '3' }).click();
  await page.getByRole('button', { name: '結果を見る' }).click();

  await expect(page.getByRole('heading', { name: 'クイズ完了！' })).toBeVisible();
  await expect(page.getByText('正答率 100%', { exact: true })).toBeVisible();
});
