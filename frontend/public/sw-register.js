if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').then(function (reg) {
    window.__swRegistration = reg;
    window.dispatchEvent(new CustomEvent('sw-registered', { detail: reg }));
    reg.addEventListener('updatefound', function () {
      var nw = reg.installing;
      if (!nw) return;
      nw.addEventListener('statechange', function () {
        if (nw.state === 'installed' && navigator.serviceWorker.controller) {
          window.location.reload();
        }
      });
    });
  }).catch(function (err) {
    console.error('[SW] Erro ao registar:', err);
  });
}
