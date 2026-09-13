import { expect, test } from '@playwright/test';

const PIXEL_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

test('quiz result shows evolution celebration when API reports evolved', async ({ page }) => {
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
      ]),
    });
  });

  await page.route('**/api/quiz/complete', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        score_percent: 100,
        correct: 1,
        total: 1,
        saved: true,
        gained_xp: 10,
        details: [],
        growth: {
          evolved: true,
          previous_stage: 'baby',
          stage: 'child',
          exp_gained: 10,
          image_url: PIXEL_PNG,
          next_stage_preview_url: PIXEL_PNG,
          hero_preview_url: PIXEL_PNG,
        },
      }),
    });
  });

  await page.goto('/quiz?subject=math&level=1');
  await page.getByRole('button', { name: '2' }).click();
  await page.getByRole('button', { name: '結果を見る' }).click();

  await expect(page.getByRole('heading', { name: '進化したよ！' })).toBeVisible();
  await expect(page.getByText('ベビー')).toBeVisible();
  await expect(page.getByText('こども')).toBeVisible();
  await expect(page.getByText('この先の進化')).toBeVisible();
});
