import { useEffect, useMemo, useRef, useState } from 'react';
import { SessionToolbar } from './SessionToolbar';
import { StatusWindow } from './StatusWindow';
import { TutorialGuide } from './TutorialGuide';
import type { ChatHistoryItem, GameMessage, RoleplayBootstrap, SessionSummary, StatusSnapshot } from '../types';

interface MainGamePageProps {
  bootstrap: RoleplayBootstrap;
  onBack: () => void;
}

const IMAGE_COMMAND_PATTERN = /<img="([a-z0-9_]+)">/gi;

function getCsrfToken() {
  if (typeof document === 'undefined') {
    return '';
  }

  const cookieValue = document.cookie
    .split(';')
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith('csrftoken='));

  return cookieValue ? decodeURIComponent(cookieValue.split('=').slice(1).join('=')) : '';
}

function formatStoryContext(snapshot?: StatusSnapshot | null) {
  const date = snapshot?.date?.trim() || '--';
  const time = snapshot?.time?.trim() || '--:--';
  const location = snapshot?.location?.trim() || 'Unknown';
  return `${date} | ${time} | ${location}`;
}

function shouldShowStoryContext(message: GameMessage) {
  return message.role !== 'user';
}

function sanitizeVisibleContent(content: string) {
  return content
    .replace(/<Status>[\s\S]*?<\/Status>/gi, '')
    .replace(/^[\s[\](){},'"`-]*(Stress|Crack Stage|Current Thought|Inner Thought|Thought|Location|Date|Time)\s*:\s*.*$/gim, '')
    .replace(/<\/?(Planning|Draft|Review|Revision)>/gi, '')
    .replace(/^\s*`{2,}\s*/g, '')
    .replace(/^\s*`{2,}\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function isDialogueLine(line: string) {
  const trimmed = line.trim();
  return /^\([^)]+\)\s*:/.test(trimmed) || /^[\"“”].*[\"“”]$/.test(trimmed);
}

function stripDialogueSpeaker(line: string) {
  return line.replace(/^\(([^)]+)\)\s*:\s*/, '');
}

function renderTextBlock(message: GameMessage, text: string, keyPrefix: string) {
  const lines = text.split('\n');

  return (
    <div className="space-y-2 whitespace-pre-wrap">
      {lines.map((line, index) => {
        const isDialogue = isDialogueLine(line);
        const isEmpty = line.trim() === '';
        const displayLine = isDialogue ? stripDialogueSpeaker(line) : line;

        return (
          <p
            key={`${keyPrefix}-${index}`}
            className={
              message.role === 'user'
                ? 'font-mono text-[#302012]'
                : isDialogue
                  ? 'text-[#5d6733]'
                  : 'text-[#4A3728]'
            }
          >
            {message.role === 'user'
              ? index === 0
                ? `> ${displayLine}`
                : displayLine
              : isEmpty
                ? ' '
                : displayLine}
          </p>
        );
      })}
    </div>
  );
}

function renderMessageBody(message: GameMessage, typedText?: string) {
  const visibleText = typedText ?? message.content;
  if (message.role === 'user') {
    return renderTextBlock(message, visibleText, message.id);
  }

  const segments = visibleText.split(IMAGE_COMMAND_PATTERN);
  const imageUrl = message.imageUrl?.trim();
  const imageCommand = message.imageCommand?.trim().toLowerCase();

  return (
    <div className="space-y-2.5">
      {segments.map((segment, index) => {
        if (index % 2 === 1) {
          const command = segment.trim().toLowerCase();
          if (!imageUrl || (imageCommand && imageCommand !== command)) {
            return null;
          }

          return (
            <div key={`${message.id}-image-${index}`} className="flex justify-center py-1">
              <div className="w-2/3 max-w-[280px] min-w-[180px] border border-white/95 bg-[#fffdf8] p-2 shadow-[0_10px_22px_rgba(74,55,40,0.14)]">
                <img
                  src={imageUrl}
                  alt={command}
                  className="block h-auto w-full object-cover shadow-[0_2px_10px_rgba(74,55,40,0.10)]"
                  loading="lazy"
                />
              </div>
            </div>
          );
        }

        if (!segment.trim() && !segment.includes('\n')) {
          return null;
        }

        return (
          <div key={`${message.id}-text-${index}`}>
            {renderTextBlock(message, segment, `${message.id}-text-${index}`)}
          </div>
        );
      })}
    </div>
  );
}

function normalizeHistoryMessage(item: ChatHistoryItem, nickname: string): GameMessage {
  const normalizedRole = item.role === nickname ? 'user' : 'assistant';

  return {
    id: `history-${item.id}`,
    role: normalizedRole,
    content: sanitizeVisibleContent(item.content),
    storyContext: formatStoryContext(item.status_snapshot),
    sourceRole: item.role,
    imageCommand: item.image_command,
    imageUrl: item.image_url,
  };
}

export function MainGamePage({ bootstrap, onBack }: MainGamePageProps) {
  const [nickname, setNickname] = useState(bootstrap.defaultNickname);
  const [draftNickname, setDraftNickname] = useState(bootstrap.defaultNickname);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<SessionSummary | null>(null);
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [input, setInput] = useState('');
  const [currentText, setCurrentText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showCursor, setShowCursor] = useState(true);
  const [typingDots, setTypingDots] = useState(0);
  const [isBusy, setIsBusy] = useState(false);
  const [connectionState, setConnectionState] = useState<'idle' | 'loading' | 'connecting' | 'ready' | 'processing' | 'error'>('idle');
  const [systemNotice, setSystemNotice] = useState('Create a session or load an existing one to begin.');
  const [showGuide, setShowGuide] = useState(false);
  const [showSessionMenu, setShowSessionMenu] = useState(false);
  const [showNewPlayerModal, setShowNewPlayerModal] = useState(false);
  const [newGameModalDismissible, setNewGameModalDismissible] = useState(false);
  const [showContinueModal, setShowContinueModal] = useState(false);
  const [selectedContinueSessionId, setSelectedContinueSessionId] = useState('');
  const [initialSessionCheckComplete, setInitialSessionCheckComplete] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const archivedScrollRef = useRef<HTMLDivElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const lastUserIndex = useMemo(
    () => [...messages].map((message) => message.role).lastIndexOf('user'),
    [messages],
  );

  const focusStartIndex = useMemo(() => {
    if (messages.length === 0) {
      return 0;
    }
    if (lastUserIndex >= 0) {
      return lastUserIndex;
    }
    return Math.max(messages.length - 1, 0);
  }, [lastUserIndex, messages.length]);

  const archivedMessages = useMemo(() => messages.slice(0, focusStartIndex), [focusStartIndex, messages]);
  const focusMessages = useMemo(() => messages.slice(focusStartIndex), [focusStartIndex, messages]);
  const lastFocusAssistant = useMemo(
    () => [...focusMessages].reverse().find((message) => message.role === 'assistant') ?? null,
    [focusMessages],
  );

  useEffect(() => {
    if (!lastFocusAssistant) {
      setCurrentText('');
      setIsTyping(false);
      return;
    }

    setIsTyping(true);
    setCurrentText('');
    let index = 0;

    const interval = window.setInterval(() => {
      if (index < lastFocusAssistant.content.length) {
        setCurrentText(lastFocusAssistant.content.slice(0, index + 1));
        index += 1;
      } else {
        setIsTyping(false);
        window.clearInterval(interval);
      }
    }, 18);

    return () => window.clearInterval(interval);
  }, [lastFocusAssistant]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setShowCursor((previous) => !previous);
    }, 530);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (connectionState !== 'processing') {
      setTypingDots(0);
      return;
    }

    const interval = window.setInterval(() => {
      setTypingDots((previous) => (previous + 1) % 4);
    }, 420);

    return () => window.clearInterval(interval);
  }, [connectionState]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (!archivedScrollRef.current || archivedMessages.length === 0) {
      return;
    }

    archivedScrollRef.current.scrollTo({
      top: archivedScrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [archivedMessages]);

  const activateSessionBySummary = async (session: SessionSummary) => {
    setActiveSession(session);
    await loadHistory(session);
    connectWebSocket(session);
  };

  const refreshActiveSession = async (sessionId: string) => {
    try {
      const response = await fetch(`${bootstrap.apiBaseUrl}/sessions/${sessionId}/`, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        return;
      }

      const session = (await response.json()) as SessionSummary;
      setActiveSession(session);
      setSessions((previous) =>
        previous.map((item) => (item.id === session.id ? session : item)),
      );
    } catch (_error) {
      // Refreshing session status is best-effort only.
    }
  };

  const loadSessions = async (options?: { autoActivateLatest?: boolean }) => {
    setIsBusy(true);
    setConnectionState('loading');
    setSystemNotice('Fetching saved sessions.');

    try {
      const response = await fetch(`${bootstrap.apiBaseUrl}/sessions/`, {
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        throw new Error('Failed to load sessions');
      }

      const data = (await response.json()) as SessionSummary[];
      setSessions(data);
      if (options?.autoActivateLatest && data.length > 0) {
        await activateSessionBySummary(data[0]);
        setSystemNotice(`Restored the latest session for ${data[0].user_nickname}.`);
        setShowNewPlayerModal(false);
        setShowContinueModal(false);
        setInitialSessionCheckComplete(true);
        return data;
      }

      if (options?.autoActivateLatest && data.length === 0) {
        setShowNewPlayerModal(true);
        setNewGameModalDismissible(false);
        setInitialSessionCheckComplete(true);
      }

      setSystemNotice(data.length > 0 ? 'Saved sessions loaded.' : 'No saved sessions were found.');
      setConnectionState(activeSession ? 'ready' : 'idle');
      return data;
    } catch (_error) {
      setSystemNotice('Could not load sessions from the backend.');
      setConnectionState('error');
      if (options?.autoActivateLatest) {
        setInitialSessionCheckComplete(true);
      }
      return [];
    } finally {
      setIsBusy(false);
    }
  };

  const loadHistory = async (session: SessionSummary) => {
    const response = await fetch(`${bootstrap.apiBaseUrl}/sessions/${session.id}/history/`, {
      headers: {
        'X-CSRFToken': getCsrfToken(),
      },
      credentials: 'same-origin',
    });

    if (!response.ok) {
      throw new Error('Failed to load history');
    }

    const data = (await response.json()) as ChatHistoryItem[];
    setMessages(data.map((item) => normalizeHistoryMessage(item, session.user_nickname)));
  };

  const connectWebSocket = (session: SessionSummary) => {
    wsRef.current?.close();
    setConnectionState('connecting');
    setSystemNotice(`Connecting to session ${session.id.slice(0, 8)}.`);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}${bootstrap.wsBasePath}/${session.id}/`);
    wsRef.current = socket;

    socket.onopen = () => {
      setConnectionState('ready');
      setSystemNotice(`Session ready for ${session.user_nickname}.`);
    };

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data) as {
        type: string;
        message: string;
        status_snapshot?: StatusSnapshot;
        image_command?: string | null;
        image_url?: string | null;
      };

      if (data.type === 'status') {
        setConnectionState('processing');
        setSystemNotice('Hari is responding.');
        return;
      }

      if (data.type === 'chat_message') {
        setMessages((previous) => [
          ...previous,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: sanitizeVisibleContent(data.message),
            storyContext: formatStoryContext(data.status_snapshot),
            sourceRole: 'NPC Engine',
            imageCommand: data.image_command,
            imageUrl: data.image_url,
          },
        ]);
        setConnectionState('ready');
        setSystemNotice('Response received.');
        await refreshActiveSession(session.id);
      }
    };

    socket.onerror = () => {
      setConnectionState('error');
      setSystemNotice('WebSocket connection encountered an error.');
    };

    socket.onclose = () => {
      setConnectionState((previous) => (previous === 'error' ? previous : 'idle'));
    };
  };

  const activateSession = async (sessionId: string) => {
    if (!sessionId) {
      return;
    }

    const target = sessions.find((session) => session.id === sessionId);
    if (!target) {
      setSystemNotice('Selected session was not found in the current list.');
      return;
    }

    setIsBusy(true);

    try {
      await activateSessionBySummary(target);
    } catch (_error) {
      setConnectionState('error');
      setSystemNotice('Failed to activate the selected session.');
    } finally {
      setIsBusy(false);
    }
  };

  const createSession = async (nicknameOverride?: string) => {
    const targetNickname = (nicknameOverride ?? nickname).trim();

    if (targetNickname.length === 0) {
      setSystemNotice('Enter a nickname before creating a session.');
      return;
    }

    setIsBusy(true);
    setConnectionState('loading');
    setSystemNotice('Creating a new session.');

    try {
      const response = await fetch(`${bootstrap.apiBaseUrl}/sessions/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          user_nickname: targetNickname,
          status_window_enabled: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const session = (await response.json()) as SessionSummary;
      setNickname(targetNickname);
      setDraftNickname(targetNickname);
      setSessions((previous) => [session, ...previous]);
      setActiveSession(session);
      setMessages([]);
      connectWebSocket(session);
      setShowSessionMenu(false);
      setShowNewPlayerModal(false);
      setShowContinueModal(false);
      setInitialSessionCheckComplete(true);
      setSystemNotice(`Session created for ${session.user_nickname}.`);
    } catch (_error) {
      setConnectionState('error');
      setSystemNotice('Could not create a new session.');
    } finally {
      setIsBusy(false);
    }
  };

  const handleSend = () => {
    if (input.trim() === '' || isTyping || !wsRef.current || connectionState === 'connecting') {
      return;
    }

    const newMessage: GameMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      storyContext: formatStoryContext({
        date: activeSession?.current_date || '',
        time: activeSession?.current_time || '',
        location: activeSession?.current_location || '',
      }),
      sourceRole: activeSession?.user_nickname ?? nickname,
    };

    setMessages((previous) => [...previous, newMessage]);
    wsRef.current.send(JSON.stringify({ message: input.trim() }));
    setInput('');
    setConnectionState('processing');
    setSystemNotice('Message sent. Waiting for the engine.');
  };

  const status = useMemo(() => {
    return {
      date: activeSession?.current_date || '--',
      time: activeSession?.current_time || '--:--',
      location: activeSession?.current_location || 'Unknown',
      stress: activeSession?.stress ?? 0,
      crackStage: activeSession?.crack_stage ?? 0,
      thought: activeSession?.current_thought ?? '',
    };
  }, [activeSession]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    void loadSessions({ autoActivateLatest: true });
  }, []);

  const handleCreateFirstSession = async () => {
    await createSession(draftNickname);
  };

  const openContinueModal = async () => {
    setShowSessionMenu(false);
    const latestSessions = await loadSessions();
    setSelectedContinueSessionId(activeSession?.id ?? latestSessions[0]?.id ?? '');
    setShowContinueModal(true);
  };

  const openNewGameModal = () => {
    setDraftNickname(activeSession?.user_nickname ?? nickname);
    setNewGameModalDismissible(true);
    setShowSessionMenu(false);
    setShowNewPlayerModal(true);
  };

  const closeNewGameModal = () => {
    if (!newGameModalDismissible) {
      return;
    }

    setShowNewPlayerModal(false);
  };

  const closeContinueModal = () => {
    setShowContinueModal(false);
  };

  const handleContinueSession = async () => {
    if (!selectedContinueSessionId) {
      return;
    }

    await activateSession(selectedContinueSessionId);
    setShowContinueModal(false);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#140e0a] px-4 pb-0 pt-2 md:px-8 md:pb-1 md:pt-3">
      <div
        className="pointer-events-none absolute -left-[10%] top-[-4%] h-[86vh] w-[42vw] min-w-[380px] rotate-[-10deg] opacity-90"
        style={{
          background:
            'linear-gradient(100deg, rgba(239, 220, 183, 0.58) 0%, rgba(224, 197, 150, 0.3) 22%, rgba(20, 14, 10, 0) 72%)',
          filter: 'blur(24px)',
        }}
      />
      <div
        className="pointer-events-none absolute -left-[6%] top-[2%] h-[34vh] w-[30vw] min-w-[280px] opacity-80"
        style={{
          background:
            'radial-gradient(circle at left top, rgba(248, 235, 206, 0.72) 0%, rgba(230, 205, 162, 0.26) 34%, rgba(20, 14, 10, 0) 74%)',
          filter: 'blur(18px)',
        }}
      />
      <div
        className="pointer-events-none absolute -right-[12%] top-[10%] h-[74vh] w-[36vw] min-w-[320px] rotate-[10deg] opacity-75"
        style={{
          background:
            'linear-gradient(255deg, rgba(235, 214, 177, 0.44) 0%, rgba(214, 181, 122, 0.18) 24%, rgba(20, 14, 10, 0) 68%)',
          filter: 'blur(28px)',
        }}
      />
      <div
        className="pointer-events-none absolute right-[-4%] top-[18%] h-[28vh] w-[24vw] min-w-[220px] opacity-60"
        style={{
          background:
            'radial-gradient(circle at right center, rgba(248, 231, 196, 0.48) 0%, rgba(221, 191, 145, 0.14) 36%, rgba(20, 14, 10, 0) 74%)',
          filter: 'blur(20px)',
        }}
      />
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-[820px] w-[820px] -translate-x-1/2 rounded-full opacity-35"
        style={{
          background: 'radial-gradient(circle, rgba(214,181,122,0.22) 0%, rgba(214,181,122,0.08) 32%, transparent 72%)',
          filter: 'blur(10px)',
        }}
      />

      <TutorialGuide open={showGuide} onClose={() => setShowGuide(false)} />

      {showNewPlayerModal && initialSessionCheckComplete && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/55 px-4">
          <div
            className="w-full max-w-md rounded-[28px] border border-[#8f745b]/70 bg-[#22160e]/95 p-6 text-[#efe3cf] shadow-2xl md:p-8"
            style={{
              boxShadow: '0 20px 60px rgba(0,0,0,0.65)',
              fontFamily: "'Noto Serif KR', serif",
            }}
          >
            <div className="mb-3 flex items-start justify-between gap-4">
              <div className="text-xs uppercase tracking-[0.24em] text-[#bfaa8d]">
                ROLEPLAY SESSION
              </div>
              {newGameModalDismissible && (
                <button
                  type="button"
                  onClick={closeNewGameModal}
                  className="rounded-full border border-[#8f745b]/70 px-3 py-1 text-xs text-[#efe3cf] transition hover:bg-[#342317]"
                >
                  ×
                </button>
              )}
            </div>
            <h2 className="mt-3 text-2xl text-[#f8f2e8]">
              새로운 게임
            </h2>
            <p className="mt-3 text-sm leading-7 text-[#d9c7ab]">
              하리가 당신에게 부를 이름입니다. 진행 도중에 변경할 수 없으니 신중하게 입력해주세요.
            </p>

            {newGameModalDismissible && (
              <p className="mt-3 text-xs tracking-[0.08em] text-[#bfaa8d]">
                모든 진행 상황은 저장됩니다.
              </p>
            )}

            <label className="mt-6 block text-xs uppercase tracking-[0.22em] text-[#bfaa8d]">
              당신의 이름
              <input
                value={draftNickname}
                onChange={(event) => setDraftNickname(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    void handleCreateFirstSession();
                  }
                }}
                className="mt-2 w-full rounded-xl border border-[#6d533d] bg-[#342317] px-4 py-3 text-sm text-[#f8f2e8] outline-none transition focus:border-[#d6b57a]"
                placeholder="Player1"
                autoFocus
                style={{ fontFamily: "'Noto Serif KR', serif" }}
              />
            </label>

            <button
              type="button"
              onClick={() => void handleCreateFirstSession()}
              disabled={isBusy || draftNickname.trim().length === 0}
              className="mt-6 w-full rounded-xl bg-[#d6b57a] px-4 py-3 text-sm font-medium text-[#25180f] transition hover:bg-[#e3c796] disabled:cursor-not-allowed disabled:opacity-50"
              style={{ fontFamily: "'Noto Serif KR', serif" }}
            >
              게임 시작
            </button>
          </div>
        </div>
      )}

      {showContinueModal && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/55 px-4">
          <div
            className="w-full max-w-lg rounded-[28px] border border-[#8f745b]/70 bg-[#22160e]/95 p-6 text-[#efe3cf] shadow-2xl md:p-8"
            style={{
              boxShadow: '0 20px 60px rgba(0,0,0,0.65)',
              fontFamily: "'Noto Serif KR', serif",
            }}
          >
            <div className="mb-3 flex items-start justify-between gap-4">
              <div className="text-xs uppercase tracking-[0.24em] text-[#bfaa8d]">
                ROLEPLAY SESSION
              </div>
              <button
                type="button"
                onClick={closeContinueModal}
                className="rounded-full border border-[#8f745b]/70 px-3 py-1 text-xs text-[#efe3cf] transition hover:bg-[#342317]"
              >
                ×
              </button>
            </div>

            <h2 className="text-2xl text-[#f8f2e8]">이어하기</h2>
            <p className="mt-3 text-sm leading-7 text-[#d9c7ab]">
              이어서 진행할 세션을 선택해 주세요.
            </p>
            <p className="mt-3 text-xs tracking-[0.08em] text-[#bfaa8d]">
              모든 진행 상황은 저장됩니다.
            </p>

            <label className="mt-6 block text-xs uppercase tracking-[0.22em] text-[#bfaa8d]">
              저장된 세션
              <select
                value={selectedContinueSessionId}
                onChange={(event) => setSelectedContinueSessionId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[#6d533d] bg-[#342317] px-4 py-3 text-sm text-[#f8f2e8] outline-none transition focus:border-[#d6b57a]"
                style={{ fontFamily: "'Noto Serif KR', serif" }}
              >
                <option value="">세션을 선택해 주세요</option>
                {sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    {new Date(session.updated_at).toLocaleString('ko-KR')} | {session.user_nickname}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="button"
              onClick={() => void handleContinueSession()}
              disabled={isBusy || selectedContinueSessionId === ''}
              className="mt-6 w-full rounded-xl bg-[#d6b57a] px-4 py-3 text-sm font-medium text-[#25180f] transition hover:bg-[#e3c796] disabled:cursor-not-allowed disabled:opacity-50"
              style={{ fontFamily: "'Noto Serif KR', serif" }}
            >
              이어서 시작하기
            </button>
          </div>
        </div>
      )}

      <div className="relative z-10 mx-auto max-w-7xl pt-1">
        <StatusWindow {...status} toolbarOpen={false} />

        <div className="relative z-20">
          <SessionToolbar
            onToggleGuide={() => setShowGuide((value) => !value)}
            menuOpen={showSessionMenu}
            onToggleMenu={() => setShowSessionMenu((value) => !value)}
            onOpenContinue={() => void openContinueModal()}
            onOpenNewGame={openNewGameModal}
            onBack={onBack}
          />
        </div>

        <div
          className="relative z-10 overflow-hidden rounded-[28px] bg-[#3d2918] p-4 shadow-2xl md:p-8"
          style={{
            boxShadow: '0 20px 60px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.1)',
          }}
        >
          <div className="flex flex-col gap-6 lg:flex-row">
            <div
              className="relative h-[min(82vh,900px)] flex-1 overflow-hidden bg-[#F4ECD8] p-6 shadow-inner md:p-8"
              style={{
                backgroundImage: `repeating-linear-gradient(
                  transparent,
                  transparent 31px,
                  rgba(74, 55, 40, 0.1) 31px,
                  rgba(74, 55, 40, 0.1) 32px
                )`,
              }}
            >
              <div className="pointer-events-none absolute left-0 top-0 h-8 w-full bg-gradient-to-b from-black/5 to-transparent" />

              <div className="flex h-full flex-col text-[#4A3728]" style={{ fontFamily: "'Noto Serif KR', serif" }}>
                <div className="mb-2 border-b border-[#4A3728]/20 pb-3 text-center">
                  <h2 className="text-xl" style={{ fontFamily: "'Crimson Text', serif" }}>
                    Hari Record
                  </h2>
                  <div className="mt-1 text-sm opacity-60">
                    {activeSession ? `Session for ${activeSession.user_nickname}` : 'Session log stays here'}
                  </div>
                </div>

                <div
                  ref={archivedScrollRef}
                  className="book-scrollbar min-h-0 flex-1 overflow-y-auto pr-2"
                >
                  {archivedMessages.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-[#4A3728]/25 p-5 text-sm leading-7 text-[#6f5947]">
                      지난 이야기의 기록이 여기에 저장됩니다. 더 나은 롤플레잉을 위해 상단의 상태창, 도움말을 참고하세요.
                    </div>
                  )}

                  <div className="space-y-6">
                    {archivedMessages.map((message) => (
                      <div key={message.id} className="text-sm leading-relaxed">
                        {shouldShowStoryContext(message) && (
                          <div className="sticky top-0 z-10 mb-1 border-b border-[#4A3728]/10 bg-[#F4ECD8] py-1 text-xs">
                            {message.storyContext}
                          </div>
                        )}
                        {renderMessageBody(message)}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div
              className="relative h-[min(82vh,900px)] flex-1 overflow-hidden bg-[#F4ECD8] p-6 shadow-inner md:p-8"
              style={{
                backgroundImage: `repeating-linear-gradient(
                  transparent,
                  transparent 31px,
                  rgba(74, 55, 40, 0.1) 31px,
                  rgba(74, 55, 40, 0.1) 32px
                )`,
              }}
            >
              <div className="pointer-events-none absolute left-0 top-0 h-8 w-full bg-gradient-to-b from-black/5 to-transparent" />

              <div className="flex h-full flex-col">
                <div className="book-scrollbar flex-1 overflow-y-auto pr-2 text-sm leading-relaxed text-[#4A3728]" style={{ fontFamily: "'Noto Serif KR', serif" }}>
                  <div className="mb-6 border-b border-[#4A3728]/20 pb-4">
                    <div className="text-xs uppercase tracking-[0.22em] opacity-55">Current Turn</div>
                    <div className="mt-1 text-xs opacity-50">
                      {focusMessages[focusMessages.length - 1]?.storyContext ?? '-- | --:-- | Unknown'}
                    </div>
                  </div>

                  {focusMessages.length === 0 && (
                    <div className="whitespace-pre-wrap text-[#6f5947]">
                      The current turn will appear here.
                    </div>
                  )}

                  <div className="space-y-6">
                    {focusMessages.map((message) => {
                      const isTypedAssistant = lastFocusAssistant?.id === message.id;
                      const visibleText = isTypedAssistant ? currentText || message.content : message.content;

                      return (
                        <div key={message.id} className="whitespace-pre-wrap">
                          {shouldShowStoryContext(message) && (
                            <div className="sticky top-0 z-10 mb-2 border-b border-[#4A3728]/10 bg-[#F4ECD8] py-1 text-xs">
                              {message.storyContext}
                            </div>
                          )}
                          <div>
                            {renderMessageBody(message, visibleText)}
                            {isTypedAssistant && isTyping && showCursor && (
                              <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-[#4A3728]" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {connectionState === 'processing' && (
                    <div className="mt-6 text-xs uppercase tracking-[0.2em] opacity-50">
                      {`Hari is typing${'.'.repeat(typingDots)}`}
                    </div>
                  )}
                </div>

                <div className="mt-6 border-t border-[#4A3728]/30 pt-4">
                  <textarea
                    ref={textAreaRef}
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Write the next action or line here."
                    disabled={!activeSession || connectionState === 'connecting'}
                    className="book-scrollbar w-full resize-none overflow-y-auto bg-transparent text-sm text-[#4A3728] placeholder:text-[#4A3728]/40 focus:outline-none"
                    style={{ fontFamily: "'Special Elite', monospace" }}
                    rows={4}
                  />

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <div className="text-xs text-[#4A3728]/55" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {!activeSession
                        ? 'Create or activate a session first.'
                        : 'Enter sends. Shift+Enter creates a new line.'}
                    </div>

                    <button
                      onClick={handleSend}
                      disabled={!activeSession || connectionState === 'connecting' || input.trim() === ''}
                      className="rounded-xl bg-[#4A3728] px-4 py-2 text-xs text-[#F4ECD8] transition-colors hover:bg-[#5a4738] disabled:cursor-not-allowed disabled:opacity-50"
                      style={{ fontFamily: "'JetBrains Mono', monospace" }}
                    >
                      Send
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            className="pointer-events-none absolute left-1/2 top-0 h-full w-8 -translate-x-1/2 bg-gradient-to-r from-black/20 via-black/40 to-black/20"
            style={{ filter: 'blur(4px)' }}
          />
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {[...Array(20)].map((_, index) => (
          <div
            key={index}
            className="absolute h-1 w-1 rounded-full bg-[#f4b942] opacity-20"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float ${5 + Math.random() * 10}s ease-in-out infinite`,
              animationDelay: `${Math.random() * 5}s`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes float {
          0%, 100% {
            transform: translateY(0) translateX(0);
            opacity: 0;
          }
          50% {
            transform: translateY(-20px) translateX(10px);
            opacity: 0.3;
          }
        }
      `}</style>
    </div>
  );
}
