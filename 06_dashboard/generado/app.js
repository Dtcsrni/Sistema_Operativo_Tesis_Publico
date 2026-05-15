const panels = [...document.querySelectorAll('.panel')];
const searchInput = document.getElementById('panel-search');
const filterButtons = [...document.querySelectorAll('.filter-btn')];
const reviewToggle = document.querySelector('[data-review-toggle]');
const reviewContent = document.querySelector('[data-review-content]');
const mdSelector = document.getElementById('md-selector');
const mdViewer = document.getElementById('md-viewer');
const REVIEW_RAIL_STORE_KEY = 'siot-review-rail';

let reviewRailCollapsed = false;

// Diagnóstico de carga
function checkLibraries() {
  const status = {
    marked: typeof marked !== 'undefined',
    mermaid: typeof mermaid !== 'undefined',
    Prism: typeof Prism !== 'undefined'
  };
  console.log('SIOT Dashboard - Status:', status);
  return status;
}

// Configuración de Mermaid
try {
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {
        fontFamily: 'Inter, system-ui, sans-serif',
        primaryColor: '#2dd4bf',
        primaryTextColor: '#fff',
        primaryBorderColor: '#14b8a6',
        lineColor: '#94a3b8',
        secondaryColor: '#3b82f6',
        tertiaryColor: '#0f172a'
      }
    });
  }
} catch (e) {
  console.error('Error inicializando Mermaid:', e);
}

function loadReviewRailState() {
  try {
    return localStorage.getItem(REVIEW_RAIL_STORE_KEY) === 'collapsed';
  } catch {
    return false;
  }
}

function renderReviewRailState() {
  if (!reviewContent || !reviewToggle) return;
  reviewContent.style.display = reviewRailCollapsed ? 'none' : 'grid';
  reviewToggle.textContent = reviewRailCollapsed ? 'Mostrar' : 'Ocultar';
  try {
    localStorage.setItem(REVIEW_RAIL_STORE_KEY, reviewRailCollapsed ? 'collapsed' : 'expanded');
  } catch {}
}

function normalize(value) {
  return (value || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function applyFilters() {
  const query = normalize(searchInput?.value);
  const activeFilter = document.querySelector('.filter-btn.is-active')?.dataset.filter || 'all';
  panels.forEach((panel) => {
    const groupMatches = activeFilter === 'all' || panel.dataset.group === activeFilter;
    const textMatches = !query || normalize(panel.innerText).includes(query);
    panel.style.display = (groupMatches && textMatches) ? '' : 'none';
  });
}

function initializeNocTabs() {
  const tabs = [...document.querySelectorAll('[data-noc-tab]')];
  const tabPanels = [...document.querySelectorAll('[data-noc-panel]')];
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.nocTab;
      tabs.forEach((item) => item.classList.toggle('is-active', item === tab));
      tabPanels.forEach((panel) => {
        panel.classList.toggle('is-active', panel.dataset.nocPanel === target);
      });
    });
  });
}

function jumpToNarrative(path) {
  const viewerSection = document.getElementById('narrativa-sistema');
  if (mdSelector && window.SIOT_NARRATIVA && window.SIOT_NARRATIVA[path]) {
    mdSelector.value = path;
    loadMarkdown(path);
    viewerSection?.scrollIntoView({ behavior: 'smooth' });
    return true;
  }
  return false;
}

async function loadMarkdown(path) {
  if (!mdViewer) return;
  try {
    mdViewer.innerHTML = '<p class="muted">Cargando ' + path + '...</p>';
    if (!window.SIOT_NARRATIVA) throw new Error('No se encontraron datos de narrativa (window.SIOT_NARRATIVA)');
    
    const text = window.SIOT_NARRATIVA[path];
    if (!text) throw new Error('No se encontró el contenido para ' + path);
    
    // 1. Renderizar Markdown a HTML
    if (typeof marked === 'undefined') throw new Error('Marked.js no está disponible');
    mdViewer.innerHTML = marked.parse(text);
    
    // 2. Preparar bloques de Mermaid
    mdViewer.querySelectorAll('pre code.language-mermaid').forEach(code => {
      const pre = code.parentElement;
      const div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code.textContent;
      pre.replaceWith(div);
    });

    // 3. Resaltar sintaxis con Prism
    if (typeof Prism !== 'undefined') {
      Prism.highlightAllUnder(mdViewer);
    }
    
    // 4. Corregir rutas de imágenes
    mdViewer.querySelectorAll('img').forEach(img => {
      const src = img.getAttribute('src');
      if (src && !src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/')) {
        // Si la ruta es interna al dashboard, quitar el prefijo
        if (src.startsWith('06_dashboard/generado/')) {
          img.src = src.replace('06_dashboard/generado/', '');
        } else {
          // Si es relativa a la raíz, subir niveles
          img.src = '../../' + src;
        }
      }
    });

    // 5. Renderizar diagramas de Mermaid
    if (typeof mermaid !== 'undefined') {
      await mermaid.run({
        nodes: mdViewer.querySelectorAll('.mermaid'),
      });
    }
    
  } catch (err) {
    console.error('Error cargando markdown:', err);
    mdViewer.innerHTML = '<div class="panel danger"><strong>Error de renderizado:</strong> ' + err.message + '</div>';
  }
}

// Inicialización principal
document.addEventListener('DOMContentLoaded', () => {
  const libStatus = checkLibraries();
  
  if (!libStatus.marked) {
    const err = document.createElement('div');
    err.className = 'panel danger';
    err.innerHTML = '<strong>Error crítico:</strong> Las librerías de renderizado no cargaron. Verifica tu conexión.';
    document.querySelector('main')?.prepend(err);
  }

  mdSelector?.addEventListener('change', (e) => loadMarkdown(e.target.value));

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      filterButtons.forEach((item) => item.classList.remove('is-active'));
      button.classList.add('is-active');
      applyFilters();
    });
  });

  searchInput?.addEventListener('input', applyFilters);

  reviewRailCollapsed = loadReviewRailState();
  reviewToggle?.addEventListener('click', () => {
    reviewRailCollapsed = !reviewRailCollapsed;
    renderReviewRailState();
  });

  renderReviewRailState();
  initializeNocTabs();

  // Intercepción de enlaces MD
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href');
    if (href && (href.endsWith('.md') || link.classList.contains('narrative-trigger'))) {
      const cleanPath = href.split('#')[0].replace(/^(\.\.\/)+/, '');
      const knownPath = Object.keys(window.SIOT_NARRATIVA || {}).find(k => k === cleanPath || k.endsWith(cleanPath));
      if (knownPath) {
        if (jumpToNarrative(knownPath)) {
          e.preventDefault();
        }
      }
    }
  });

  // Carga inicial de narrativa
  if (mdSelector) loadMarkdown(mdSelector.value);
});

if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}
