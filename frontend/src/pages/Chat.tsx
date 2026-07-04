import { getAuth } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ArrowLeft, Info, Send } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import { getApiBase } from '@/lib/apiBase';
import { fetchCharacterFromServer, loadCharacter } from '@/lib/characterState';

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

const Chat = () => {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState(() => loadCharacter().displayName);

  useEffect(() => {
    void fetchCharacterFromServer().then(() =>
      setDisplayName(loadCharacter().displayName),
    );
  }, []);

  const idRef = useRef(1);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: `${displayName}だよ〜！きょうもがんばろうね。何かあった？`,
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const [openaiConfigured, setOpenaiConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch(`${getApiBase()}/chat/capabilities`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { openai_configured?: boolean } | null) => {
        if (cancelled) return;
        if (d && typeof d.openai_configured === 'boolean') {
          setOpenaiConfigured(d.openai_configured);
        } else {
          setOpenaiConfigured(null);
        }
      })
      .catch(() => {
        if (!cancelled) setOpenaiConfigured(null);
      })
      .finally(() => {
        if (!cancelled) setCapabilitiesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const subtitle = (() => {
    if (capabilitiesLoading) return 'あいさつのじゅんび中…';
    if (openaiConfigured === true)
      return 'OpenAIのAIがおへんじするよ。むずかしいことはおとなにきいてね。';
    if (openaiConfigured === false)
      return 'きょうはサーバー内のやさしい自動へんじもーどだよ。ぶんしょうはほんばんのAIよりかんたんだよ。';
    return 'せつぞくのかくにんにしっぱいしたけど、ためしてみてね。';
  })();

  const nextId = () => {
    idRef.current += 1;
    return idRef.current;
  };

  const handleSendMessage = async () => {
    const trimmed = inputMessage.trim();
    if (!trimmed || sending) return;

    const user = getAuth().currentUser;
    if (!user) {
      toast({
        title: 'ログインが必要です',
        description: 'チャットはログイン後に使えます。',
        variant: 'destructive',
      });
      return;
    }

    const userMsg: Message = {
      id: nextId(),
      content: trimmed,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setSending(true);

    try {
      const token = await user.getIdToken();
      const res = await fetch(`${getApiBase()}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: trimmed,
          character_display_name: displayName,
        }),
      });

      let replyText =
        'ごめんね、さいしんでもう一回ためしてみよ。';

      const raw = await res.text();
      try {
        const data = JSON.parse(raw || '{}') as {
          reply?: unknown;
          detail?: unknown;
        };
        if (typeof data.reply === 'string' && data.reply.trim()) {
          replyText = data.reply.trim();
        } else if (
          typeof data.detail === 'string' &&
          (data.detail as string).trim()
        ) {
          replyText = (data.detail as string).trim();
        }
      } catch {
        if (raw.trim()) replyText = raw.trim().slice(0, 400);
      }

      const characterMessage: Message = {
        id: nextId(),
        content:
          replyText ||
          `${displayName}、ちょっとまよっちゃった…またね。`,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, characterMessage]);

      if (!res.ok) {
        toast({
          title: 'チャットサービス側の問題',
          description: `状態 ${res.status}。ローカルなら自動かいとうにもどります`,
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('API通信エラー:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          content: `${displayName}、ごめん！つうしんできなかった。またあとでもう一度ね。`,
          isUser: false,
          timestamp: new Date(),
        },
      ]);
      toast({
        title: '通信エラー',
        description: String(error ?? ''),
        variant: 'destructive',
      });
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-light via-mint-light to-sky-light p-4 flex flex-col">
      <div className="flex items-center mb-4">
        <Button
          onClick={() => navigate('/')}
          variant="ghost"
          size="sm"
          className="mr-4 text-navy-dark hover:bg-lavender-soft/20 rounded-full"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          戻る
        </Button>
        <div className="flex items-center">
          <div className="text-4xl mr-3 animate-bounce-gentle">😺</div>
          <div>
            <h1 className="text-2xl font-bold text-navy-dark">
              {displayName}とおはなし
            </h1>
            <p className="text-sm text-gray-600">{subtitle}</p>
          </div>
        </div>
      </div>

      {!capabilitiesLoading && openaiConfigured === false && (
        <Alert className="max-w-4xl mx-auto w-full mb-3 border-amber-300 bg-amber-50 text-amber-950">
          <Info className="h-4 w-4 text-amber-800" />
          <AlertTitle className="text-amber-950">やさしい自動へんじモード</AlertTitle>
          <AlertDescription className="text-amber-950/90 text-sm space-y-2">
            <p>
              いまのサーバーには <strong>OpenAI（GPT）</strong>{' '}
              のキーがはいっていないみたい（よういされてないよ）。だから、ひらがなでそろえた
              <strong>かんたんな自動ことば</strong>でおへんじしているよ。
            </p>
            <p className="text-xs">
              ほんもののチャットボットにもしたいときは、おとながバックエンドに{' '}
              <code className="rounded bg-amber-100/80 px-1">OPENAI_API_KEY</code>{' '}
              をせっていすると、ここでもAIがものがたりできるようになるよ。
            </p>
          </AlertDescription>
        </Alert>
      )}

      {!capabilitiesLoading && openaiConfigured === true && (
        <Alert className="max-w-4xl mx-auto w-full mb-3 border-emerald-200 bg-emerald-50/90 text-emerald-950">
          <Info className="h-4 w-4 text-emerald-800" />
          <AlertTitle className="text-emerald-950">AIチャットオン</AlertTitle>
          <AlertDescription className="text-emerald-950/90 text-xs">
            おとながOpenAIキーをよういしてくれたよ。ひみつのことや、からだやあんぜんホケンのききかたはできないだけど、楽しくちょうせんしてね。
          </AlertDescription>
        </Alert>
      )}

      <Card className="kid-card flex-1 flex flex-col max-w-4xl mx-auto w-full">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-96 md:max-h-[min(28rem,calc(100vh-14rem))]">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
                  message.isUser
                    ? 'bg-sky-soft text-white ml-4'
                    : 'bg-white text-navy-dark border-2 border-pink-soft/30 mr-4'
                }`}
              >
                {!message.isUser && <div className="text-xl mb-1">😺</div>}
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p
                  className={`text-xs mt-1 ${
                    message.isUser ? 'text-blue-100' : 'text-gray-500'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString('ja-JP', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`${displayName}に話しかけてみよう...`}
              className="flex-1 text-base p-3 rounded-2xl border-2 border-pink-soft/30 focus:border-sky-soft"
              disabled={sending}
            />
            <Button
              type="button"
              onClick={() => void handleSendMessage()}
              disabled={!inputMessage.trim() || sending}
              className="bg-gradient-to-r from-pink-soft to-purple-soft text-white px-6 py-3 rounded-2xl hover:scale-105 transition-transform disabled:opacity-50 disabled:hover:scale-100"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
          {sending && (
            <p className="text-xs text-gray-500 mt-2 text-center">
              {displayName}がかんがえ中…
            </p>
          )}
        </div>
      </Card>

      <div className="mt-4 max-w-4xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {[
            '今日はどんなことしたの？',
            'クイズやってみない？',
            'お散歩はした？',
          ].map((suggestion, index) => (
            <Button
              key={index}
              type="button"
              onClick={() => setInputMessage(suggestion)}
              variant="outline"
              disabled={sending}
              className="text-sm py-2 rounded-full border-purple-soft/30 text-navy-dark hover:bg-purple-soft hover:text-white"
            >
              {suggestion}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Chat;
