/* dashboard.js - Sidebar collapsible, theme, charts, user menu */
(() => {
  const sidebar = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('collapseBtn');
  const themeToggle = document.getElementById('themeToggle');
  const avatarBtn = document.getElementById('avatarBtn');
  const userDropdown = document.getElementById('userDropdown');
  const mobileMenu = document.getElementById('mobileMenu');
  const searchInput = document.getElementById('searchInput');

  const SIDEBAR_KEY = 'ghostai_sidebar_collapsed';
  const THEME_KEY = 'ghostai_theme';

  // init sidebar state
  function initSidebar() {
    const collapsed = localStorage.getItem(SIDEBAR_KEY) === '1';
    if (collapsed) sidebar.classList.add('collapsed');
    else sidebar.classList.remove('collapsed');
  }

  collapseBtn?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed') ? '1' : '0');
  });

  // mobile toggle - simply toggle sidebar show (for small screens)
  mobileMenu?.addEventListener('click', () => {
    if (sidebar.style.display === 'block') sidebar.style.display = '';
    else sidebar.style.display = 'block';
  });

  // theme handling (simple)
  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.style.setProperty('--bg', '#f5f7fa');
      document.documentElement.style.setProperty('--surface', '#ffffff');
      document.documentElement.style.setProperty('--text', '#141618');
      document.documentElement.style.setProperty('--muted', '#5b636b');
      themeToggle.textContent = '🌞';
    } else {
      document.documentElement.style.removeProperty('--bg');
      document.documentElement.style.removeProperty('--surface');
      document.documentElement.style.removeProperty('--text');
      document.documentElement.style.removeProperty('--muted');
      themeToggle.textContent = '🌙';
    }
    localStorage.setItem(THEME_KEY, theme);
  }

  themeToggle?.addEventListener('click', () => {
    const current = localStorage.getItem(THEME_KEY) || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
  });

  // load saved theme
  (function(){
    const saved = localStorage.getItem(THEME_KEY) || 'dark';
    applyTheme(saved);
  })();

  // user menu
  avatarBtn?.addEventListener('click', (ev) => {
    userDropdown.classList.toggle('visible');
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.user-menu')) {
      userDropdown.classList.remove('visible');
    }
  });

  // keyboard shortcut for search (Ctrl/Cmd+K)
  document.addEventListener('keydown', (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') {
      ev.preventDefault();
      searchInput.focus();
    }
  });

  // ---------- Charts (Chart.js) ----------
  function makeCharts(){
    try {
      const ctx1 = document.getElementById('leadsChart').getContext('2d');
      const leadsChart = new Chart(ctx1, {
        type: 'line',
        data: {
          labels: ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
          datasets: [{
            label: 'Leads',
            data: [8, 12, 9, 14, 18, 10, 11],
            borderColor: '#42c3ff',
            backgroundColor: 'rgba(66,195,255,0.12)',
            tension: 0.35,
            fill: true,
            pointRadius: 3
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#99a0ad' } },
            y: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#99a0ad' } }
          }
        }
      });

      const ctx2 = document.getElementById('volumeChart').getContext('2d');
      const volumeChart = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: ['Jan','Fev','Mar','Abr','Mai','Jun'],
          datasets: [{
            label: 'Mensagens',
            data: [420, 380, 460, 520, 490, 610],
            backgroundColor: '#2bb673'
          }]
        },
        options:{
          responsive:true,
          plugins:{ legend:{ display:false } },
          scales: {
            x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#99a0ad' } },
            y: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#99a0ad' } }
          }
        }
      });

    } catch (err) {
      console.warn('Chart creation failed', err);
    }
  }

  // Wait DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    makeCharts();
  });

})();
