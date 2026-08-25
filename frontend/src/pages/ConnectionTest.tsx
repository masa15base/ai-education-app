import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { getApiBase } from '@/lib/apiBase';

const DIRECT_HEROKU_HEALTH =
  'https://ai-edu-app-backend-fb6ffb49064a.herokuapp.com/api/health';

function explainFetchFailure(
  err: unknown,
  pageOrigin: string,
  apiBaseUsed: string,
): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg !== 'Failed to fetch' && !msg.includes('NetworkError')) {
    return msg;
  }

  const usingProxy =
    typeof apiBaseUsed === 'string' && apiBaseUsed === '/api';
  const healthUrl = `${apiBaseUsed.replace(/\/$/, '')}/health`;

  return [
    msg,
    '',
    usingProxy
      ? '【開発サーバー経由 `/api`] Vite が Heroku に中継します。ダメな場合は vite.config の BACKEND_PROXY_TARGET、または `npm run dev` を再起動してください。'
      : '【対処のヒント】クロスオリジン経由では CORS（Heroku の FRONTEND_ORIGINS）を確認してください。',
    '',
    `このページのオリジン（Heroku に追加する値）:\n  ${pageOrigin}`,
    '',
    'Heroku CLI の例（アプリ名はあなたのバックエンドに合わせる）:',
    `  heroku config:set FRONTEND_ORIGINS="${pageOrigin}" -a ai-edu-app-backend`,
    '',
    '既に FRONTEND_ORIGINS がある場合はカンマで追記:',
    '  heroku config:get FRONTEND_ORIGINS',
    '  heroku config:set FRONTEND_ORIGINS="新しいオリジン,既存の値..."',
    '',
    '※ 直接 Heroku を叩いて CORS 切り分けする場合:',
    `  ${DIRECT_HEROKU_HEALTH}`,
    '',
    usingProxy ? `同一オリジンでのヘルス（プロキシ）: ${healthUrl}` : `  ${healthUrl}`,
  ].join('\n');
}

type RowState = 'idle' | 'loading' | 'ok' | 'fail';

interface CheckRow {
  label: string;
  state: RowState;
  detail?: string;
}

function badge(state: RowState) {
  if (state === 'loading')
    return (
      <span className="inline-flex items-center gap-1 text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> 確認中
      </span>
    );
  if (state === 'ok')
    return <span className="text-green-600 font-semibold">OK</span>;
  if (state === 'fail')
    return <span className="text-red-600 font-semibold">NG</span>;
  return <span className="text-gray-400">—</span>;
}

const ConnectionTest = () => {
  const [pageOrigin, setPageOrigin] = useState('');
  const [rows, setRows] = useState<CheckRow[]>([
    {
      label: 'API の取りに行き先（開発は /api ＝プロキシ）',
      state: 'idle',
      detail: '',
    },
    { label: 'GET /api/health', state: 'idle' },
    {
      label:
        'GET 診断（/health?…、/diagnostic、/health/diagnostic を順に試行）',
      state: 'idle',
    },
    { label: 'Firebase Auth（ログイン状態）', state: 'idle' },
    { label: 'GET /api/progress（要ログイン）', state: 'idle' },
    { label: 'GET /api/steps/today（認証なし）', state: 'idle' },
    { label: 'GET /api/chat/capabilities', state: 'idle' },
    { label: 'GET /api/stats/summary（認証なし）', state: 'idle' },
    { label: 'GET /api/preprocess-image/info', state: 'idle' },
    {
      label:
        'PUT /api/steps/today（ログイン時・GET の値を再送して往復確認）',
      state: 'idle',
    },
    { label: 'GET /api/questions/bank-stats（問題バンク）', state: 'idle' },
  ]);

  const updateRow = (index: number, patch: Partial<CheckRow>) => {
    setRows((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...patch };
      return next;
    });
  };

  useEffect(() => {
    const origin =
      typeof window !== 'undefined' ? window.location.origin : '';
    setPageOrigin(origin);
    const base = getApiBase();
    const row0detail =
      import.meta.env.DEV && import.meta.env.VITE_DEV_API_PROXY !== 'false'
        ? `${base}\n実体: vite.config の BACKEND_PROXY_TARGET → Heroku`
        : [
            base,
            import.meta.env.VITE_API_URL
              ? '（VITE_API_URL / VITE_DEV_API_PROXY で制御）'
              : '',
          ]
            .filter(Boolean)
            .join('\n');

    updateRow(0, { state: 'ok', detail: row0detail });

    const run = async () => {
      updateRow(1, { state: 'loading' });
      try {
        const r = await fetch(`${base}/health`);
        const j = await r.json().catch(() => ({}));
        updateRow(1, {
          state: r.ok ? 'ok' : 'fail',
          detail: `${r.status} ${JSON.stringify(j)}`,
        });
      } catch (e) {
        updateRow(1, {
          state: 'fail',
          detail: explainFetchFailure(e, origin, base),
        });
      }

      updateRow(2, { state: 'loading' });
      const diagAttempts: [string, string][] = [
        [`${base}/health?include_diagnostic=true`, 'GET /health?include_diagnostic=true'],
        [`${base}/diagnostic`, 'GET /diagnostic'],
        [`${base}/health/diagnostic`, 'GET /health/diagnostic'],
      ];
      try {
        const tried: string[] = [];
        let okPayload: Record<string, unknown> | null = null;
        let via = '';
        for (const [url, label] of diagAttempts) {
          try {
            const r = await fetch(url);
            const j = (await r.json().catch(() => null)) as
              | Record<string, unknown>
              | null;
            tried.push(`${label}=${r.status}`);
            if (
              r.ok &&
              j &&
              typeof j.database_configured === 'boolean'
            ) {
              okPayload = j;
              via = label;
              break;
            }
          } catch {
            tried.push(`${label}=error`);
          }
        }

        if (okPayload && via) {
          updateRow(2, {
            state: 'ok',
            detail: `${via}\n${JSON.stringify(okPayload, null, 2)}`,
          });
        } else {
          updateRow(2, {
            state: 'fail',
            detail: [
              'いずれの経路でも診断用 JSON が得られませんでした。',
              '試行:',
              tried.join(' | ') || '(なし)',
              '',
              'Heroku にこのリポジトリの最新バックエンドがデプロイされているか確認してください。',
              DIRECT_HEROKU_HEALTH + '?include_diagnostic=true はブラウザで開いて確認できます。',
            ].join('\n'),
          });
        }
      } catch (e) {
        updateRow(2, {
          state: 'fail',
          detail: explainFetchFailure(e, origin, base),
        });
      }

      const extraChecks: [number, string][] = [
        [5, `${base}/steps/today`],
        [6, `${base}/chat/capabilities`],
        [7, `${base}/stats/summary?timeline_limit=1`],
        [8, `${base}/preprocess-image/info`],
        [10, `${base}/questions/bank-stats`],
      ];
      for (const [idx, url] of extraChecks) {
        updateRow(idx, { state: 'loading' });
        try {
          const r = await fetch(url);
          const j = await r.json().catch(() => ({}));
          updateRow(idx, {
            state: r.ok ? 'ok' : 'fail',
            detail: `${r.status}\n${JSON.stringify(j, null, 2).slice(0, 1200)}`,
          });
        } catch (e) {
          updateRow(idx, {
            state: 'fail',
            detail: explainFetchFailure(e, origin, base),
          });
        }
      }
    };

    void run();
  }, []);

  useEffect(() => {
    const auth = getAuth();
    updateRow(3, { state: 'loading' });
    const unsub = onAuthStateChanged(auth, (user) => {
      updateRow(3, {
        state: 'ok',
        detail: user
          ? `ログイン中（uid: ${user.uid.slice(0, 8)}…）`
          : '未ログイン（履歴APIテストはスキップされます）',
      });

      updateRow(4, { state: 'loading' });
      updateRow(9, { state: 'loading' });
      void (async () => {
        if (!auth.currentUser) {
          updateRow(4, {
            state: 'ok',
            detail: 'スキップ（ログイン後に再読み込みで確認）',
          });
          updateRow(9, {
            state: 'ok',
            detail: 'スキップ（ログイン後に再読み込みで確認）',
          });
          return;
        }
        const token = await auth.currentUser.getIdToken();
        const base = getApiBase();

        try {
          const r = await fetch(`${base}/progress`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const text = await r.text();
          updateRow(4, {
            state: r.ok ? 'ok' : 'fail',
            detail: `${r.status} ${text.slice(0, 300)}`,
          });
        } catch (e) {
          updateRow(4, {
            state: 'fail',
            detail: e instanceof Error ? e.message : String(e),
          });
        }

        try {
          const g = await fetch(`${base}/steps/today`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const gj = (await g.json().catch(() => ({}))) as {
            steps?: unknown;
          };
          const cur =
            typeof gj.steps === 'number' && Number.isFinite(gj.steps)
              ? Math.max(0, Math.round(gj.steps))
              : 0;
          const p = await fetch(`${base}/steps/today`, {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ steps: cur }),
          });
          const pj = await p.json().catch(() => ({}));
          updateRow(9, {
            state: p.ok ? 'ok' : 'fail',
            detail: [
              `GET ${g.status} → 再送 steps=${cur}`,
              `PUT ${p.status} ${JSON.stringify(pj)}`,
            ].join('\n'),
          });
        } catch (e) {
          updateRow(9, {
            state: 'fail',
            detail: e instanceof Error ? e.message : String(e),
          });
        }
      })();
    });
    return () => unsub();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/">
              <ArrowLeft className="h-4 w-4 mr-2" />
              ホーム
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">ユーザー接続テスト</h1>
        </div>

        {pageOrigin && (
          <Card className="p-4 mb-4 bg-amber-50 border-amber-200">
            <p className="text-sm font-medium text-amber-900">
              いまのアプリのオリジン（CORS に追加する値）
            </p>
            <code className="mt-2 block text-sm break-all bg-white p-2 rounded border">
              {pageOrigin}
            </code>
            <p className="text-xs text-amber-800 mt-2">
              開発中は通常 <code className="bg-amber-100 px-1">/api</code>{' '}
              プロキシを使うため CORS は不要です。Heroku に直接ブラウザから叩くときだけ、
              Heroku の{' '}
              <code className="bg-amber-100 px-1">FRONTEND_ORIGINS</code>{' '}
              にこのオリジンを追加してください。
            </p>
          </Card>
        )}

        <Card className="p-6 mb-4">
          <p className="text-sm text-gray-600 mb-4">
            ブラウザからバックエンド・Firebase・（ログイン時）進捗 API・歩数 PUT の往復・歩数／チャット／統計／前処理アルゴリズム情報の公開 GET
            への到達を確認します。CORS エラーの場合はバックエンドの{' '}
            <code className="bg-gray-100 px-1 rounded">FRONTEND_ORIGINS</code>{' '}
            を確認してください。
          </p>
          <ul className="space-y-4">
            {rows.map((row, i) => (
              <li
                key={i}
                className="border-b border-gray-100 pb-3 last:border-0 last:pb-0"
              >
                <div className="flex justify-between items-start gap-4">
                  <span className="font-medium">{row.label}</span>
                  {badge(row.state)}
                </div>
                {row.detail && (
                  <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto whitespace-pre-wrap break-all">
                    {row.detail}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        </Card>

        <Button variant="outline" onClick={() => window.location.reload()}>
          再テスト
        </Button>
      </div>
    </div>
  );
};

export default ConnectionTest;
