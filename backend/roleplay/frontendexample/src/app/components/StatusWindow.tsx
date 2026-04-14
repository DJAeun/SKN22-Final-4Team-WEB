import { useEffect, useRef, useState } from 'react';

interface StatusWindowProps {
  date: string;
  time: string;
  location: string;
  stress: number;
  crackStage: number;
  thought: string;
  toolbarOpen: boolean;
}

function StatusCard({
  date,
  time,
  location,
  stress,
  crackStage,
  thought,
  showThought,
  onToggleThought,
}: StatusWindowProps & {
  showThought: boolean;
  onToggleThought: () => void;
}) {
  const isHighStress = stress >= 70;

  return (
    <div
      className="w-[264px] rounded-2xl border border-[#d8c6a9] bg-[#f7efe2]/96 p-4 text-[#4a3728] shadow-2xl"
      style={{ fontFamily: "'Noto Serif KR', serif" }}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.25em] text-[#8b6f57]">
            Status Log
          </div>
          <div className="mt-1 text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {date} {time}
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="mb-2 text-[11px] uppercase tracking-[0.22em] text-[#8b6f57]">
          Location
        </div>
        <div
          className="inline-flex rounded-full bg-[#b6483f] px-3 py-1 text-xs text-white"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          {location}
        </div>
      </div>

      <div className="mb-4">
        <div className="mb-2 text-[11px] uppercase tracking-[0.22em] text-[#8b6f57]">
          Stage Progress
        </div>
        <div className="relative h-4 overflow-hidden rounded-full bg-[#4a3728]/15">
          <div
            className={`h-full transition-all duration-500 ${isHighStress ? 'bg-[#b6483f]' : 'bg-[#4a3728]'
              }`}
            style={{ width: `${stress}%` }}
          />
          <div
            className="absolute inset-0 flex items-center justify-center text-[10px]"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            {stress}%
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="mb-2 text-[11px] uppercase tracking-[0.22em] text-[#8b6f57]">
          Stage
        </div>
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className={`flex size-9 items-center justify-center rounded-lg border ${level <= crackStage
                ? 'border-[#b6483f] bg-[#b6483f]/10 text-[#b6483f]'
                : 'border-[#4a3728]/20 text-[#4a3728]/30'
                }`}
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              {level}
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-[#4a3728]/15 pt-4">
        <button
          type="button"
          onClick={onToggleThought}
          className="rounded-full border border-[#4a3728]/20 px-3 py-1 text-[11px] uppercase tracking-[0.18em] hover:bg-[#eadbc4]"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          {showThought ? '속마음 닫기' : '속마음 보기'}
        </button>
        {showThought && (
          <div className="mt-3 text-sm italic leading-6">
            "{thought || '아직 파싱된 속마음이 없습니다.'}"
          </div>
        )}
      </div>
    </div>
  );
}

export function StatusWindow({
  date,
  time,
  location,
  stress,
  crackStage,
  thought,
  toolbarOpen,
}: StatusWindowProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showThought, setShowThought] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const toggleThought = () => setShowThought((value) => !value);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (!wrapperRef.current) {
        setIsHovered(false);
        return;
      }

      const rect = wrapperRef.current.getBoundingClientRect();
      const inOverlay =
        event.clientX >= rect.left &&
        event.clientX <= rect.right &&
        event.clientY >= rect.top &&
        event.clientY <= rect.bottom;

      const inTriggerStrip =
        event.clientX >= rect.left &&
        event.clientX <= rect.right &&
        event.clientY >= rect.top &&
        event.clientY <= rect.top + 64;

      if (toolbarOpen) {
        setIsHovered(false);
        return;
      }

      setIsHovered((previous) => (previous ? inOverlay : inTriggerStrip));
    };

    const handleMouseLeaveWindow = () => {
      setIsHovered(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeaveWindow);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeaveWindow);
    };
  }, [toolbarOpen]);

  useEffect(() => {
    if (toolbarOpen) {
      setIsHovered(false);
    }
  }, [toolbarOpen]);

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen((value) => !value)}
        className="fixed left-4 top-4 z-40 rounded-full border border-[#d9c7ab] bg-[#f7efe2] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#4a3728] shadow-lg md:hidden"
      >
        상태창
      </button>

      <div
        ref={wrapperRef}
        className="absolute left-0 top-16 z-0 hidden md:block pointer-events-none"
        style={{
          transform: `translate(${toolbarOpen ? 32 : 32}px, ${toolbarOpen ? 0 : -56}px)`,
        }}
      >
        <div className="relative w-[264px]">
          <StatusCard
            date={date}
            time={time}
            location={location}
            stress={stress}
            crackStage={crackStage}
            thought={thought}
            showThought={showThought}
            onToggleThought={toggleThought}
          />
        </div>
      </div>

      <div
        className={`absolute left-0 top-16 hidden md:block transition-opacity duration-300 ${isHovered ? 'z-30 opacity-100' : 'pointer-events-none z-[5] opacity-0'
          }`}
        style={{
          transform: `translate(${toolbarOpen ? 32 : 32}px, ${toolbarOpen ? 0 : -56}px)`,
        }}
      >
        <div className="relative w-[264px]">
          <StatusCard
            date={date}
            time={time}
            location={location}
            stress={stress}
            crackStage={crackStage}
            thought={thought}
            showThought={showThought}
            onToggleThought={toggleThought}
          />
        </div>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/35 p-4 md:hidden" onClick={() => setMobileOpen(false)}>
          <div
            className="ml-auto max-w-sm rounded-2xl border border-[#d8c6a9] bg-[#f7efe2] p-4 text-[#4a3728] shadow-2xl"
            onClick={(event) => event.stopPropagation()}
            style={{ fontFamily: "'Noto Serif KR', serif" }}
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm uppercase tracking-[0.25em] text-[#8b6f57]">Status Log</div>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-full border border-[#4a3728]/20 px-3 py-1 text-xs uppercase"
              >
                닫기
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                {date} {time}
              </div>
              <div>{location}</div>
              <div>Stress: {stress}%</div>
              <div>Crack Stage: {crackStage}</div>
              <button
                type="button"
                onClick={toggleThought}
                className="rounded-full border border-[#4a3728]/20 px-3 py-1 text-xs uppercase"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                {showThought ? '속마음 닫기' : '속마음 보기'}
              </button>
              {showThought && <div className="italic">"{thought || '아직 파싱된 속마음이 없습니다.'}"</div>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
