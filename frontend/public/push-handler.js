// Push notification handler — loaded via importScripts() in the generated service worker
// Written in plain ES5 to avoid any transpilation issues.

self.addEventListener('push', function (event) {
  if (!event.data) return;
  var data;
  try { data = event.data.json(); } catch (e) { data = { title: 'Helpdesk', body: event.data.text() }; }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Helpdesk Escolar', {
      body: data.body || '',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-96x96.png',
      data: { url: data.url || '/' },
      tag: 'helpdesk',
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var target = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clients) {
      var existing = clients.find(function (c) { return c.url.indexOf(self.location.origin) === 0; });
      if (existing) {
        existing.focus();
        return existing.navigate(target);
      }
      return self.clients.openWindow(target);
    })
  );
});
