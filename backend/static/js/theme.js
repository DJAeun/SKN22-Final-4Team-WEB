/**
 * 🌙 Theme Manager — Dark/Light Mode Toggle
 * 모든 페이지에서 전역적으로 작동하는 테마 전환 시스템
 */

(function initTheme() {
  // 저장된 테마 읽기 (기본값: 'light')
  const saved = localStorage.getItem('hari-theme') || 'light';

  // 문서에 적용
  document.documentElement.setAttribute('data-theme', saved);

  // 초기 로드 완료 후 DOM 업데이트
  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.classList.add(saved === 'dark' ? 'on' : 'off');
    }
    const chatBtn = document.getElementById('chat-theme-toggle');
    if (chatBtn) {
      chatBtn.classList.add(saved === 'dark' ? 'on' : 'off');
    }
  });

  // 페이지 로드 시에도 적용 (스크립트 로드 후 지연 적용)
  setTimeout(() => {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.classList.toggle('on', saved === 'dark');
      btn.classList.toggle('off', saved !== 'dark');
    }
    const chatBtn = document.getElementById('chat-theme-toggle');
    if (chatBtn) {
      chatBtn.classList.toggle('on', saved === 'dark');
      chatBtn.classList.toggle('off', saved !== 'dark');
    }
  }, 50);
})();

/**
 * 테마 전환 함수
 */
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'light';
  const next = current === 'light' ? 'dark' : 'light';

  // HTML에 적용
  html.setAttribute('data-theme', next);

  // 로컬스토리지에 저장
  localStorage.setItem('hari-theme', next);

  // 홈페이지 버튼 상태 업데이트
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.classList.toggle('on', next === 'dark');
    btn.classList.toggle('off', next !== 'dark');
  }

  // 채팅 페이지 버튼 상태 업데이트
  const chatBtn = document.getElementById('chat-theme-toggle');
  if (chatBtn) {
    chatBtn.classList.toggle('on', next === 'dark');
    chatBtn.classList.toggle('off', next !== 'dark');
  }
}

/**
 * 현재 테마 가져오기
 */
function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}
