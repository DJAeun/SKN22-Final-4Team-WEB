(function () {
  const BALANCE_KEY = 'hari-sari-balance';
  const STARTER_GRANTED_KEY = 'hari-sari-starter-granted';
  const STARTER_AMOUNT = 200;
  const CHAT_COST = 10;
  const ROLEPLAY_COST = 20;

  function normalizeAmount(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return 0;
    return Math.max(0, Math.floor(amount));
  }

  function getBalance() {
    return normalizeAmount(localStorage.getItem(BALANCE_KEY) || '0');
  }

  function setBalance(amount) {
    const nextAmount = normalizeAmount(amount);
    localStorage.setItem(BALANCE_KEY, String(nextAmount));
    syncBalanceElements();
    return nextAmount;
  }

  function addBalance(amount) {
    return setBalance(getBalance() + normalizeAmount(amount));
  }

  function spend(amount) {
    const cost = normalizeAmount(amount);
    const current = getBalance();
    if (current < cost) return false;
    setBalance(current - cost);
    return true;
  }

  function grantStarterIfNeeded() {
    if (localStorage.getItem(STARTER_GRANTED_KEY) === 'true') {
      return false;
    }
    addBalance(STARTER_AMOUNT);
    localStorage.setItem(STARTER_GRANTED_KEY, 'true');
    return true;
  }

  function formatSari(amount) {
    return normalizeAmount(amount).toLocaleString('ko-KR') + ' SARI';
  }

  function getRemainingCount(cost) {
    return Math.floor(getBalance() / normalizeAmount(cost || 1));
  }

  function syncBalanceElements() {
    const balance = getBalance();
    document.querySelectorAll('[data-sari-balance]').forEach((el) => {
      el.textContent = formatSari(balance);
    });
    document.querySelectorAll('[data-sari-chat-remaining]').forEach((el) => {
      el.textContent = getRemainingCount(CHAT_COST).toLocaleString('ko-KR') + '회';
    });
    document.querySelectorAll('[data-sari-roleplay-remaining]').forEach((el) => {
      el.textContent = getRemainingCount(ROLEPLAY_COST).toLocaleString('ko-KR') + '회';
    });
    document.querySelectorAll('[data-sari-starter-amount]').forEach((el) => {
      el.textContent = formatSari(STARTER_AMOUNT);
    });
  }

  window.HariSariWallet = {
    BALANCE_KEY,
    STARTER_GRANTED_KEY,
    STARTER_AMOUNT,
    CHAT_COST,
    ROLEPLAY_COST,
    getBalance,
    setBalance,
    addBalance,
    spend,
    grantStarterIfNeeded,
    formatSari,
    getRemainingCount,
    syncBalanceElements,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      grantStarterIfNeeded();
      syncBalanceElements();
    });
  } else {
    grantStarterIfNeeded();
    syncBalanceElements();
  }
})();
