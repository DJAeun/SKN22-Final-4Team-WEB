interface SessionToolbarProps {
  menuOpen: boolean;
  onToggleGuide: () => void;
  onToggleMenu: () => void;
  onOpenContinue: () => void;
  onOpenNewGame: () => void;
  onBack: () => void;
}

export function SessionToolbar({
  menuOpen,
  onToggleGuide,
  onToggleMenu,
  onOpenContinue,
  onOpenNewGame,
  onBack,
}: SessionToolbarProps) {
  return (
    <div className="mb-4 flex justify-end">
      <div className="relative flex items-start gap-3">
        <button
          type="button"
          onClick={onToggleGuide}
          className="rounded-xl border border-[#d6b57a]/70 bg-[#25180f]/90 px-4 py-2 text-xs tracking-[0.12em] text-[#f6e8cf] shadow-xl transition hover:bg-[#3c2a1d]"
        >
          도움말
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={onToggleMenu}
            className="rounded-xl border border-[#d6b57a]/70 bg-[#25180f]/90 px-4 py-2 text-xs tracking-[0.12em] text-[#f6e8cf] shadow-xl transition hover:bg-[#3c2a1d]"
          >
            게임 불러오기
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-[calc(100%+12px)] z-30 w-48 rounded-2xl border border-[#8f745b]/70 bg-[#22160e]/95 p-3 shadow-2xl">
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={onOpenContinue}
                  className="rounded-xl border border-[#6d533d] bg-[#342317] px-4 py-3 text-sm text-[#f8f2e8] transition hover:bg-[#463022]"
                >
                  이어하기
                </button>
                <button
                  type="button"
                  onClick={onOpenNewGame}
                  className="rounded-xl bg-[#d6b57a] px-4 py-3 text-sm font-medium text-[#25180f] transition hover:bg-[#e3c796]"
                >
                  새 게임
                </button>
              </div>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => { window.location.href = '/'; }}
          className="flex items-center gap-2 rounded-xl border border-[#d6b57a]/40 bg-[#25180f]/90 px-4 py-2 text-xs tracking-[0.12em] text-[#d6b57a] shadow-xl transition hover:border-[#d6b57a]/80 hover:bg-[#3c2a1d] hover:text-[#f6e8cf]"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          <span className="text-sm leading-none">←</span>
          <span>메인으로</span>
        </button>
      </div>
    </div>
  );
}
