(() => {
  const sidebar = document.querySelector('.sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  const menu = document.querySelector('[data-menu-toggle]');
  function closeMenu() {
    sidebar?.classList.remove('open');
    scrim?.classList.remove('open');
    menu?.setAttribute('aria-expanded', 'false');
  }
  menu?.addEventListener('click', () => {
    const open = !sidebar.classList.contains('open');
    sidebar.classList.toggle('open', open);
    scrim.classList.toggle('open', open);
    menu.setAttribute('aria-expanded', String(open));
  });
  scrim?.addEventListener('click', closeMenu);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });

  const scenario = document.querySelector('[data-scenario-display]');
  if (scenario) {
    const phases = {
      baseline: {
        title: 'Baseline · all paths open',
        description: 'With no blocked client, the priority-0 NORMAL flow forwards IPv4 and ARP across the single L2 segment.',
        count: '0 drop rules',
        routes: { h1h2: '0% loss', h3h2: '0% loss', h1h3: '0% loss' }
      },
      blocked: {
        title: 'Blocked · h2 isolated for IPv4',
        description: 'Priority-100 source and destination matches for 10.0.0.2 win over normal forwarding. h1 and h3 still communicate.',
        count: '2 drop rules',
        routes: { h1h2: '100% loss', h3h2: '100% loss', h1h3: '0% loss' }
      },
      recovery: {
        title: 'Recovery · original connectivity restored',
        description: 'DELETE_STRICT removes both h2 drops. The priority-0 NORMAL rule remains, so no network restart is needed.',
        count: '0 drop rules',
        routes: { h1h2: '0% loss', h3h2: '0% loss', h1h3: '0% loss' }
      }
    };
    const buttons = document.querySelectorAll('[data-scenario-choice]');
    function setScenario(name) {
      const phase = phases[name];
      if (!phase) return;
      scenario.dataset.state = name;
      scenario.querySelector('[data-scenario-title]').textContent = phase.title;
      scenario.querySelector('[data-scenario-description]').textContent = phase.description;
      scenario.querySelector('[data-scenario-count]').textContent = phase.count;
      Object.entries(phase.routes).forEach(([route, value]) => {
        const result = scenario.querySelector(`[data-route="${route}"] .route-result`);
        if (!result) return;
        result.textContent = value;
        result.classList.toggle('allow', value === '0% loss');
        result.classList.toggle('drop', value !== '0% loss');
      });
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.scenarioChoice === name)));
    }
    buttons.forEach(button => button.addEventListener('click', () => setScenario(button.dataset.scenarioChoice)));
    setScenario(scenario.dataset.state || 'baseline');
  }

  const filters = document.querySelectorAll('[data-filter]');
  const evidenceCards = document.querySelectorAll('[data-category]');
  filters.forEach(button => button.addEventListener('click', () => {
    const selected = button.dataset.filter;
    filters.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    evidenceCards.forEach(card => { card.hidden = selected !== 'all' && !card.dataset.category.split(' ').includes(selected); });
  }));

  const dialog = document.querySelector('[data-lightbox]');
  if (dialog) {
    const image = dialog.querySelector('img');
    const title = dialog.querySelector('[data-lightbox-title]');
    document.querySelectorAll('[data-lightbox-src]').forEach(button => button.addEventListener('click', () => {
      image.src = button.dataset.lightboxSrc;
      image.alt = button.dataset.lightboxTitle || 'Evidence screenshot';
      title.textContent = button.dataset.lightboxTitle || 'Evidence screenshot';
      dialog.showModal();
    }));
    dialog.querySelector('[data-lightbox-close]')?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  }
})();
