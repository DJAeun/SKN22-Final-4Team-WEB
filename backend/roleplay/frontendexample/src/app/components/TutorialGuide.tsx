import { useState } from 'react';

interface TutorialGuideProps {
  open: boolean;
  onClose: () => void;
}

export function TutorialGuide({ open, onClose }: TutorialGuideProps) {
  const [showWorkHelp, setShowWorkHelp] = useState(false);

  if (!open) {
    return null;
  }

  return (
    <>
      <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/35 p-4 md:p-8">
        <div className="w-full max-w-xl rounded-2xl border border-[#d6c4aa] bg-[#f7efe2] p-6 text-[#3e2d20] shadow-2xl">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-[#7b5f49]">
                도움말
              </div>
              <h2
                className="text-2xl"
                style={{ fontFamily: "'Crimson Text', serif", fontWeight: 600 }}
              >
                화면 사용 안내
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[#7b5f49]/30 px-3 py-1 text-xs uppercase tracking-[0.2em] hover:bg-[#efe1ca]"
            >
              닫기
            </button>
          </div>

          <div className="space-y-6 text-sm leading-7">
            <section>
              <h3 className="text-base font-semibold text-[#4b382b]">입력 방식</h3>
              <p className="mt-2">
                괄호 안에는 행동이나 상황 설명을, 괄호 밖에는 실제 대사를 입력해 주세요.
              </p>
              <p className="mt-2 text-[#6a5240]">
                예: (탕비실 안 공기가 어색하게 가라앉는다. 나는 하리의 눈치를 살핀다.) 지금
                잠깐 말씀드려도 될까요?
              </p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-[#4b382b]">Stage</h3>
              <p className="mt-2">
                Stage는 이야기의 진행 정도를 나타냅니다.
              </p>
              <p className="mt-2 text-[#6a5240]">
                진행에 따라 상황의 분위기와 하리의 반응, 관계의 결이 조금씩 달라질 수
                있습니다.
              </p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-[#4b382b]">저장 방식</h3>
              <p className="mt-2">
                게임은 대화와 선택에 따라 계속 이어지며, 모든 진행 상황은 자동으로 저장됩니다.
              </p>
            </section>

            <div className="border-t border-[#d8c6aa] pt-4">
              <button
                type="button"
                onClick={() => setShowWorkHelp(true)}
                className="rounded-full border border-[#7b5f49]/30 px-4 py-2 text-xs uppercase tracking-[0.18em] hover:bg-[#efe1ca]"
              >
                업무가 어려워요
              </button>
            </div>
          </div>
        </div>
      </div>

      {showWorkHelp && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/45 p-4 md:p-8">
          <div className="w-full max-w-2xl rounded-2xl border border-[#d6c4aa] bg-[#f7efe2] p-6 text-[#3e2d20] shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.28em] text-[#7b5f49]">
                  업무 안내
                </div>
                <h2
                  className="text-2xl"
                  style={{ fontFamily: "'Crimson Text', serif", fontWeight: 600 }}
                >
                  회사와 플레이 팁
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setShowWorkHelp(false)}
                className="rounded-full border border-[#7b5f49]/30 px-3 py-1 text-xs uppercase tracking-[0.2em] hover:bg-[#efe1ca]"
              >
                닫기
              </button>
            </div>

            <div className="space-y-4 text-sm leading-7">
              <p>
                Vertex Intelligence Group (VIG)는 여의도 소재의 AI&amp;딥러닝 솔루션
                기업으로, 업무 진행에 고난이도의 지식이 필요할 수 있습니다.
              </p>
              <p>
                본 롤플레잉에서는 더 나은 플레이 경험을 위해 상황을 쉽게 표현하거나, 스킵할 수
                있습니다.
              </p>
              <p className="text-[#6a5240]">
                "(주어진 업무가 잘 안 풀린다. 파트장에게 보고한다.) 파트장님께서 지시하신 작업,
                잘 안 됩니다. 확인 부탁드립니다."
              </p>
              <p className="text-[#6a5240]">
                "(길었던 업무 시간이 지나고, 어느덧 퇴근 시간이 되었다.) 파트장님은 퇴근 안
                하세요?"
              </p>
              <p>
                위와 같이 묘사하면 어려운 업무는 간단히 넘기고, 시간과 공간 이동도 자연스럽게
                진행할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
