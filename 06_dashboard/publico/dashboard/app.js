const panels = [...document.querySelectorAll('.panel')];
const searchInput = document.getElementById('panel-search');
const filterButtons = [...document.querySelectorAll('.filter-btn')];
const tokenOverlay = document.getElementById('token-overlay');
const reviewToggle = document.querySelector('[data-review-toggle]');
const reviewContent = document.querySelector('[data-review-content]');
const tokenBudgetDisplay = document.querySelector('[data-token-budget-display]');
const tokenUsedDisplay = document.querySelector('[data-token-used-display]');
const tokenRemainingDisplay = document.querySelector('[data-token-remaining-display]');
const tokenRatioDisplay = document.querySelector('[data-token-ratio-display]');
const tokenBudgetInput = document.querySelector('[data-token-budget-input]');
const tokenUsedInput = document.querySelector('[data-token-used-input]');
const tokenMeter = document.querySelector('[data-token-meter]');
const tokenHint = document.querySelector('[data-token-hint]');
const tokenCollapse = document.querySelector('[data-token-collapse]');
const tokenAdjustButtons = [...document.querySelectorAll('[data-token-adjust]')];
const tokenResetButton = document.querySelector('[data-token-reset]');
const TOKEN_STORE_KEY = 'codex-token-budget-overlay';
const REVIEW_RAIL_STORE_KEY = 'codex-review-rail';
const TOKEN_DEFAULT_BUDGET = Number(tokenOverlay?.dataset.defaultBudget || 0);
const TOKEN_DEFAULT_USED = Number(tokenOverlay?.dataset.defaultUsed || 0);
let reviewRailCollapsed = false;

function clampTokenValue(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(0, Math.round(parsed));
}

function todayKey() {
  return new Date().toLocaleDateString('en-CA');
}

function loadReviewRailState() {
  try {
    return localStorage.getItem(REVIEW_RAIL_STORE_KEY) === 'collapsed';
  } catch {
    return false;
  }
}

function renderReviewRailState() {
  if (!reviewToggle || !reviewContent) {
    return;
  }
  reviewContent.classList.toggle('is-collapsed', reviewRailCollapsed);
  reviewToggle.setAttribute('aria-expanded', String(!reviewRailCollapsed));
  reviewToggle.textContent = reviewRailCollapsed ? 'Mostrar' : 'Ocultar';
  try {
    localStorage.setItem(REVIEW_RAIL_STORE_KEY, reviewRailCollapsed ? 'collapsed' : 'expanded');
  } catch {}
}

function loadTokenState() {
  const fallback = {
    budget: TOKEN_DEFAULT_BUDGET,
    used: TOKEN_DEFAULT_USED,
    collapsed: false,
    date: todayKey(),
  };

  try {
    const raw = localStorage.getItem(TOKEN_STORE_KEY);
    if (!raw) {
      return fallback;
    }

    const parsed = JSON.parse(raw);
    const currentDate = todayKey();
    if (parsed.date !== currentDate) {
      return { ...fallback, budget: clampTokenValue(parsed.budget) || TOKEN_DEFAULT_BUDGET, date: currentDate };
    }

    return {
      budget: clampTokenValue(parsed.budget) || TOKEN_DEFAULT_BUDGET,
      used: clampTokenValue(parsed.used),
      collapsed: Boolean(parsed.collapsed),
      date: currentDate,
    };
  } catch {
    return fallback;
  }
}

let tokenState = loadTokenState();

function saveTokenState() {
  localStorage.setItem(TOKEN_STORE_KEY, JSON.stringify(tokenState));
}

function renderTokenState() {
  const budget = clampTokenValue(tokenState.budget) || TOKEN_DEFAULT_BUDGET;
  const used = Math.min(clampTokenValue(tokenState.used), budget);
  const remaining = Math.max(budget - used, 0);
  const ratio = budget > 0 ? Math.round((used / budget) * 100) : 0;
  const mode = remaining === 0 ? 'límite alcanzado' : remaining < budget * 0.2 ? 'modo bajo' : remaining < budget * 0.5 ? 'modo medio' : 'modo amplio';

  tokenState = { ...tokenState, budget, used, date: todayKey() };
  if (tokenOverlay) {
    tokenOverlay.classList.toggle('is-collapsed', Boolean(tokenState.collapsed));
  }
  if (tokenCollapse) {
    tokenCollapse.setAttribute('aria-pressed', String(Boolean(tokenState.collapsed)));
    tokenCollapse.textContent = tokenState.collapsed ? 'Mostrar' : 'Ocultar';
  }
  if (tokenBudgetDisplay) tokenBudgetDisplay.textContent = String(budget);
  if (tokenUsedDisplay) tokenUsedDisplay.textContent = String(used);
  if (tokenRemainingDisplay) tokenRemainingDisplay.textContent = String(remaining);
  if (tokenRatioDisplay) tokenRatioDisplay.textContent = `${ratio}%`;
  if (tokenBudgetInput) tokenBudgetInput.value = String(budget);
  if (tokenUsedInput) tokenUsedInput.value = String(used);
  if (tokenMeter) {
    tokenMeter.max = String(budget || 1);
    tokenMeter.value = String(used);
    tokenMeter.setAttribute('aria-valuetext', `${remaining} restantes de ${budget}`);
  }
  if (tokenHint) {
    tokenHint.textContent = `${mode}: mantiene visible el margen útil mientras trabajas.`;
  }
  saveTokenState();
}

function updateTokenState(patch) {
  tokenState = {
    ...tokenState,
    ...patch,
    budget: clampTokenValue(patch.budget ?? tokenState.budget),
    used: clampTokenValue(patch.used ?? tokenState.used),
  };
  renderTokenState();
}

function normalize(value) {
  return (value || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '');
}

function applyFilters() {
  const query = normalize(searchInput?.value);
  const activeFilter = document.querySelector('.filter-btn.is-active')?.dataset.filter || 'all';
  panels.forEach((panel) => {
    const groupMatches = activeFilter === 'all' || panel.dataset.group === activeFilter;
    const textMatches = !query || normalize(panel.innerText).includes(query);
    panel.classList.toggle('is-hidden', !(groupMatches && textMatches));
  });
}

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    filterButtons.forEach((item) => item.classList.remove('is-active'));
    button.classList.add('is-active');
    applyFilters();
  });
});

searchInput?.addEventListener('input', applyFilters);
applyFilters();

tokenBudgetInput?.addEventListener('change', () => {
  updateTokenState({ budget: tokenBudgetInput.value });
});

tokenUsedInput?.addEventListener('change', () => {
  updateTokenState({ used: tokenUsedInput.value });
});

tokenAdjustButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const delta = clampTokenValue(button.dataset.tokenAdjust);
    const signedDelta = button.dataset.tokenAdjust?.startsWith('-') ? -delta : delta;
    updateTokenState({ used: tokenState.used + signedDelta });
  });
});

tokenResetButton?.addEventListener('click', () => {
  updateTokenState({ used: 0 });
});

tokenCollapse?.addEventListener('click', () => {
  tokenState = { ...tokenState, collapsed: !tokenState.collapsed };
  renderTokenState();
});

reviewRailCollapsed = loadReviewRailState();
reviewToggle?.addEventListener('click', () => {
  reviewRailCollapsed = !reviewRailCollapsed;
  renderReviewRailState();
});

renderTokenState();
renderReviewRailState();

if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}
