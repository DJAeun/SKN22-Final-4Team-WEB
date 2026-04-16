import { useEffect, useRef, useState } from 'react';
import { Lock } from 'lucide-react';

interface NDAEntrancePageProps {
  onAccept: () => void;
  defaultNickname: string;
}

function setupCanvas(canvas: HTMLCanvasElement) {
  const context = canvas.getContext('2d');
  if (!context) {
    return null;
  }

  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.fillStyle = '#0c0907';
  context.fillRect(0, 0, rect.width, rect.height);
  context.strokeStyle = '#d6b57a';
  context.lineWidth = 2;
  context.lineCap = 'round';

  return context;
}

function getCanvasPoint(
  canvas: HTMLCanvasElement,
  event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>,
) {
  const rect = canvas.getBoundingClientRect();
  const clientX = 'touches' in event ? event.touches[0].clientX : event.clientX;
  const clientY = 'touches' in event ? event.touches[0].clientY : event.clientY;

  return {
    x: clientX - rect.left,
    y: clientY - rect.top,
  };
}

export function NDAEntrancePage({ onAccept, defaultNickname }: NDAEntrancePageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);

  const startDrawing = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const point = getCanvasPoint(canvas, event);
    context.beginPath();
    context.moveTo(point.x, point.y);
    setIsDrawing(true);
    setHasSignature(true);
  };

  const draw = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    if ('touches' in event) {
      event.preventDefault();
    }

    const point = getCanvasPoint(canvas, event);
    context.lineTo(point.x, point.y);
    context.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    setupCanvas(canvas);
    setHasSignature(false);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    setupCanvas(canvas);

    const handleResize = () => {
      setupCanvas(canvas);
      setHasSignature(false);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#120d09] p-4 py-16">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            'radial-gradient(circle at top, rgba(214,181,122,0.26), transparent 45%), linear-gradient(180deg, #1f140d 0%, #0c0907 100%)',
        }}
      />

      {/* 왼쪽 사이드바 */}
      <div className="fixed left-0 top-0 flex h-full w-16 flex-col items-center justify-between border-r border-[#d6b57a]/20 bg-[#0f0b08] py-8">
        <button
          className="group flex flex-col items-center gap-2 text-[#d6b57a]/60 transition-colors hover:text-[#f4e3c2]"
          title="보안 접근 안내"
        >
          <Lock className="h-6 w-6" />
          <div
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '7px',
              letterSpacing: '0.08em',
              whiteSpace: 'nowrap',
              marginTop: '8px',
              color: 'inherit',
            }}
          >
            RESTRICTED
          </div>
        </button>
      </div>

      {/* 오른쪽 상단 뒤로가기 버튼 */}
      <a
        href="/"
        className="fixed right-5 top-5 z-50 flex items-center gap-2 border border-[#d6b57a]/40 bg-[#0f0b08]/90 px-4 py-2 text-[#d6b57a]/70 backdrop-blur-sm transition-all hover:border-[#d6b57a]/80 hover:bg-[#1a1208]/90 hover:text-[#f4e3c2]"
        style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', letterSpacing: '0.15em' }}
        title="메인 홈으로 돌아가기"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        MAIN
      </a>

      <div
        className="fixed inset-0 pointer-events-none opacity-10"
        style={{
          background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, #d6b57a 2px, #d6b57a 4px)',
          animation: 'scan 10s linear infinite',
        }}
      />

      <div className="relative z-10 w-full max-w-4xl border border-[#d6b57a]/70 bg-[#18110d] shadow-[0_0_40px_rgba(214,181,122,0.18)]">
        <div className="bg-[#d6b57a] p-6 text-[#1a120d]">
          <div className="flex items-center justify-between">
            <div>
              <div
                className="mb-1 text-xs tracking-[0.3em]"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                VIG CONFIDENTIAL
              </div>
              <h1
                className="text-2xl tracking-tight"
                style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}
              >
                HARI PROJECT DATA ACCESS
              </h1>
            </div>
            <div
              className="text-sm"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              CLASS: INTERNAL
            </div>
          </div>
        </div>

        <div className="p-8 text-[#f5ead6]">
          <div style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
            <h2 className="mb-4 text-xl" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              기밀 열람 동의 및 튜토리얼
            </h2>

            <div className="space-y-4 text-sm leading-relaxed">
              <p>
                본 화면은 하리 롤플레잉 게임에 진입하는 모든 플레이어에게 적용되는 안내 페이지입니다.
              </p>

              <p>
                당신은 유명 AI & 소프트웨어 회사인 VIG의 신입 개발자로서 롤플레잉을 시작합니다.
              </p>

              <p>
                또한 같은 부서 파트장인 27세 '하리'와의 공감적 접근을 통한 관계 발전을 목표로 합니다.
              </p>


              <div className="my-6 border border-[#d6b57a]/30 bg-[#d6b57a]/10 p-4">
                <h3
                  className="mb-3 text-base text-[#f3ddba]"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  이용 가이드
                </h3>

                <div className="space-y-2 text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">01</span>
                    <span>이야기가 주어지면, 플레이어는 상황에 맞는 응답을 제출해 롤플레잉을 진행할 수 있습니다.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">02</span>
                    <span>당신의 응답은 시스템에 전달되어, 하리를 포함한 주변 상황의 반응을 이끌어냅니다.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">03</span>
                    <span>
                      괄호 안에는 행동이나 상황 설명을, 괄호 밖에는 실제 대사를 입력해 주세요.
                      <br />
                      예: (어느덧 퇴근 시간이 되었다. 나는 작업했던 백엔드 설계문서를 정리하고 퇴근 준비를
                      한다. 아직 집중해 일하고 있는 하리를 보며 걱정한다.) 파트장님은 퇴근 안 하세요?
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">04</span>
                    <span>현재 상태를 확인하고 싶다면, 화면 좌측 상단에 마우스를 올려 상태창을 확인해주세요.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">05</span>
                    <span>가이드 버튼을 통해 튜토리얼을 언제든 다시 열어볼 수 있습니다.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#d6b57a]">06</span>
                    <span>다음 이야기가 쓰여질 때까지 최대 5분 정도 소요될 수 있습니다.</span>
                  </div>
                </div>
              </div>

              <p className="text-xs text-[#d6b57a]">
                본 롤플레잉 게임은 예측 불가능한 심리적 반응을 포함할 수 있습니다. 폭력적이거나 선정적인 내용을 포함할 수 있습니다.
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-[#d6b57a]/25 p-8">
          <div className="mb-4">
            <label
              className="mb-2 block text-sm text-[#f3ddba]"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              전자 서명
            </label>
            <div className="relative">
              <canvas
                ref={canvasRef}
                width={600}
                height={120}
                className="w-full cursor-crosshair touch-none border-2 border-[#d6b57a] bg-[#0c0907]"
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseLeave={stopDrawing}
                onTouchStart={startDrawing}
                onTouchMove={draw}
                onTouchEnd={stopDrawing}
              />
              {hasSignature && (
                <button
                  onClick={clearSignature}
                  className="absolute right-2 top-2 text-xs text-[#d6b57a] transition-colors hover:text-[#f3ddba]"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  지우기
                </button>
              )}
            </div>
          </div>

          <button
            onClick={onAccept}
            disabled={!hasSignature}
            className="w-full bg-[#d6b57a] py-4 text-lg tracking-wider text-[#18110d] shadow-[0_0_18px_rgba(214,181,122,0.35)] transition-all hover:bg-[#e7c995] disabled:cursor-not-allowed disabled:opacity-50"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}
          >
            동의하고 게임 시작하기
          </button>
        </div>
      </div>

      <style>{`
        @keyframes scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
      `}</style>
    </div>
  );
}
