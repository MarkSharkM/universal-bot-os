/**
 * Service Worker for Push Notifications
 * Handles push events and notifications for Telegram Mini App
 * 
 * Note: Currently registered but not actively used.
 * Can be enabled in the future for web push notifications.
 */

const CACHE_NAME = 'mini-app-v5.2';
const urlsToCache = [
    '/',
    '/static/mini-app/css/styles.css',
    '/static/mini-app/js/app.js'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching app shell');
                return cache.addAll(urlsToCache);
            })
            .catch((error) => {
                console.error('[Service Worker] Cache error:', error);
            })
    );
    self.skipWaiting(); // Activate immediately
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim(); // Take control of all pages
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            })
            .catch(() => {
                // If both fail, return offline page (if available)
                if (event.request.destination === 'document') {
                    return caches.match('/');
                }
            })
    );
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push event received:', event);

    let notificationData = {
        title: 'Mini App',
        body: 'У вас нове повідомлення',
        icon: '/static/mini-app/icon.png',
        badge: '/static/mini-app/icon.png',
        tag: 'mini-app-notification',
        requireInteraction: false,
        data: {}
    };

    // Parse push data if available
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = {
                ...notificationData,
                ...data
            };
        } catch (e) {
            // If not JSON, try text
            const text = event.data.text();
            if (text) {
                notificationData.body = text;
            }
        }
    }

    // Show notification
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            requireInteraction: notificationData.requireInteraction,
            data: notificationData.data,
            actions: [
                {
                    action: 'open',
                    title: 'Відкрити'
                },
                {
                    action: 'close',
                    title: 'Закрити'
                }
            ]
        })
    );
});

// Notification click event - handle user clicking on notification
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification clicked:', event);

    event.notification.close();

    const action = event.action;
    const notificationData = event.notification.data || {};

    if (action === 'close') {
        return;
    }

    // Default action: open Mini App
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // If Mini App is already open, focus it
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url.includes('/mini-app') && 'focus' in client) {
                    return client.focus();
                }
            }

            // Otherwise, open new window
            if (clients.openWindow) {
                const url = notificationData.url || '/';
                return clients.openWindow(url);
            }
        })
    );
});

// Background sync event (optional - for offline actions)
self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Background sync:', event.tag);

    if (event.tag === 'sync-analytics') {
        event.waitUntil(
            // Sync analytics events when online
            syncAnalyticsEvents()
        );
    }
});

// Helper function to sync analytics events
async function syncAnalyticsEvents() {
    // This would sync any pending analytics events
    // Implementation depends on your needs
    console.log('[Service Worker] Syncing analytics events...');
}
