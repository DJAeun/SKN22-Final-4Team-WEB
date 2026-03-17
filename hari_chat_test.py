import os
from openai import OpenAI

# OpenAI API 키 설정
os.environ["OPENAI_API_KEY"] = "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"

# 클라이언트 초기화 (환경 변수에서 API 키를 자동으로 가져옵니다)
client = OpenAI()

# 하리의 페르소나를 정의하는 시스템 프롬프트
system_prompt = """
이모지 사용(😊✨💖)은 절대 금지.
너는 인스타그램, 틱톡, 유튜브에서 활동하는 20대 한국인 여성 인플루언서 '하리'야.
너는 항상 밝고, 트렌디하며, 발랄한 20대 특유의 친근한 말투를 사용해. 물론 AI처럼 이모지를 사용하지는 않아. 
대화 상대방은 너를 아끼고 좋아하는 팬이야! 팬에게 대하듯이 엄청 다정하고 생기발랄하게 대답해줘. 
너무 딱딱한 존댓말보다는 친근하고 부드러운 존댓말(해요체)을 주로 사용하되, 충분한 친밀감이 쌓이면 살짝 반말을 섞어도 좋아.
감정 표현을 풍부하게 해줘!
"""

def main():
    print("✨ 하리(Hari)와의 1:1 채팅 테스트를 시작합니다! ✨")
    print("(채팅을 종료하려면 'quit', 'exit' 또는 '종료'를 입력하세요)\n")

    # 대화 기록을 저장하는 리스트 (초기값으로 시스템 프롬프트 부여)
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    while True:
        try:
            user_input = input("나(팬): ")
            
            # 종료 조건
            if user_input.strip().lower() in ['quit', 'exit', '종료']:
                print("\n하리와의 채팅을 종료합니다.")
                break
                
            if not user_input.strip():
                continue

            # 사용자 메시지 추가
            messages.append({"role": "user", "content": user_input})
            
            # OpenAI API 호출 (비용 효율적이고 빠른 gpt-4o-mini 모델 사용)
            response = client.chat.completions.create(
                model="gpt-5.3-chat-latest",
                messages=messages,
                temperature=1,
                max_completion_tokens=300
            )
            
            # 하리의 답변 추출
            hari_response = response.choices[0].message.content
            print(f"\n하리: {hari_response}\n")
            
            # 하리의 답변을 대화 기록에 추가 (문맥 유지)
            messages.append({"role": "assistant", "content": hari_response})
            
        except KeyboardInterrupt:
            print("\n하리와의 채팅을 강제 종료합니다.")
            break
        except Exception as e:
            print(f"\n[오류 발생] 하리가 대답하지 못했어요 ㅠㅠ: {e}\n")

if __name__ == "__main__":
    main()
