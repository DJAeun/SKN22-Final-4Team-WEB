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
    updateAllThemeButtons(saved);
  });

  // 페이지 로드 시에도 적용 (스크립트 로드 후 지연 적용)
  setTimeout(() => {
    updateAllThemeButtons(saved);
  }, 50);
})();

/**
 * 모든 테마 버튼 업데이트
 */
function updateAllThemeButtons(theme) {
  const isDark = theme === 'dark';

  // 모든 theme-toggle 버튼 업데이트
  document.querySelectorAll('#theme-toggle, #chat-theme-toggle').forEach(btn => {
    btn.classList.toggle('on', isDark);
    btn.classList.toggle('off', !isDark);
  });
}

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

  // 모든 테마 버튼 상태 업데이트
  updateAllThemeButtons(next);
}

/**
 * 현재 테마 가져오기
 */
function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}
