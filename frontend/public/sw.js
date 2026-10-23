self.addEventListener("push", (event) => {
  const payload = { title: "ProENEM Lab", body: "", url: "/", tag: "proenem" };
  try {
    Object.assign(payload, event.data ? event.data.json() : {});
  } catch (_error) {

  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      tag: payload.tag,
      data: { url: payload.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((item) => item.url.includes(target) && "focus" in item);
      if (open) return open.focus();
      if (clients.openWindow) return clients.openWindow(target);
      return undefined;
    })
  );
});
