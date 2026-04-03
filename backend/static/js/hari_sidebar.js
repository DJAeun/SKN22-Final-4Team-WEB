/**
 * hari_sidebar.js — 하리 상태창 Mock Data
 *
 * 추후 API 연동 시:
 *   fetch('/api/hari/status/').then(r => r.json()).then(data => HariSidebar.init(data));
 * 로 교체하면 됩니다. 데이터 구조는 HARI_DATA 객체와 동일하게 맞추세요.
 */

const HARI_DATA = {

  /** 1. 하리 소개 */
  profile: {
    intro: "안녕! 나는 하리야 😊\n테크 뉴스를 쉽게 전달하고 팬들이랑 소통하는 걸 제일 좋아해.\n모르는 거 뭐든 물어봐도 돼!",
    likes: ["🎵 음악 듣기", "☕ 카페 탐방", "📱 테크 트렌드", "🌸 봄 산책"],
    dislikes: ["😓 악의적인 질문", "🚫 사생활 침해", "💢 욕설·비하 표현"]
  },

  /** 2. 지금 하리는 */
  status: {
    availableTime: "오전 10시 ~ 오후 11시",
    busyLevel: "여유",          // "여유" | "조금 바빠요" | "많이 바빠요"
    mood: "🌸",
    moodText: "오늘 기분 좋아요!",
    music: {
      artist: "NewJeans",
      title: "Supernatural"
    }
  },

  /** 3. 오늘 하리가 얘기하고 싶은 것 */
  topics: [
    { label: "🤖 요즘 AI 근황 물어보기",  text: "요즘 AI 트렌드 어때? 최신 소식 알려줘!" },
    { label: "🌸 봄 노래 추천받기",        text: "요즘 봄 감성 노래 추천해줘!" },
    { label: "☕ 카페 얘기 하기",          text: "요즘 좋았던 카페 있어? 추천해줘!" }
  ],

  /** 4. 자주 묻는 질문 */
  faq: [
    {
      question: "하리 직업이 뭐야?",
      answer: "나는 테크 뉴스를 전달하고 팬들이랑 소통하는 콘텐츠 크리에이터야! 유튜브랑 여기서 활동 중이야 😊"
    },
    {
      question: "어떤 콘텐츠 올려?",
      answer: "주로 IT·AI 관련 뉴스를 쉽게 풀어서 Shorts로 올리고 있어! 어렵지 않게 설명하는 게 목표야 🎯"
    },
    {
      question: "멤버십 혜택이 뭐야?",
      answer: "FAN, FAN+, BORI 3가지 플랜이 있어! BORI 플랜이면 나랑 롤플레잉 대화도 할 수 있어 ✨ 멤버십 페이지에서 확인해봐!"
    },
    {
      question: "팬이 되려면 어떻게 해?",
      answer: "일단 회원가입하고 멤버십 가입하면 돼! 그리고 지금처럼 나한테 말 걸어줘 😆💕"
    }
  ],

  /** 5. 대화 예절 */
  etiquette: [
    "사생활 관련 질문은 조금 어려워요 🥲",
    "욕설이나 비하 표현은 대화가 어려워요 😢",
    "너무 개인적인 연락처 요청은 NO! 🙅‍♀️",
    "서로 존중하는 대화면 더 신나게 얘기할 수 있어요 💕"
  ],

  /** 6. 이전 대화 요약 (mock — API 연동 시 /api/chat/summaries/ 로 교체) */
  chatSummaries: [
    {
      date: "2026-04-03",
      label: "오늘",
      preview: "AI 트렌드랑 봄 노래 얘기했어 🌸",
      topics: ["AI 트렌드", "봄 노래 추천"]
    },
    {
      date: "2026-04-02",
      label: "어제",
      preview: "테크 뉴스랑 카페 추천 얘기했어 ☕",
      topics: ["구글 Stitch", "카페 추천"]
    },
    {
      date: "2026-03-31",
      label: "3월 31일",
      preview: "멤버십이랑 롤플레잉에 대해 물어봤어 ✨",
      topics: ["멤버십 안내", "BORI 플랜"]
    }
  ]
};
