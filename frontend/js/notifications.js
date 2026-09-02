// notifications.js
const notificationsManager = {
    _pollingInterval: null,
    _isOpen: false,

    init() {
        // Charger les notifications
        this.loadNotifications();

        // Ouvrir/fermer le dropdown au clic sur la cloche
        document.getElementById('notificationBell').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // Fermer le dropdown en cliquant ailleurs
        document.addEventListener('click', () => {
            if (this._isOpen) {
                this.closeDropdown();
            }
        });

        // Marquer tout comme lu
        document.getElementById('markAllReadBtn').addEventListener('click', () => {
            this.markAllRead();
        });

        // Polling toutes les 30 secondes pour les nouvelles notifications
        this._pollingInterval = setInterval(() => {
            this.loadNotifications(false);
        }, 30000);
    },

    async loadNotifications(showLoading = true) {
        try {
            const data = await api.getNotifications();
            this.renderNotifications(data);
            // Mettre à jour le badge
            document.getElementById('notificationBadge').textContent = data.unread_count || 0;
            if (data.unread_count > 0) {
                document.getElementById('notificationBadge').style.display = 'block';
            } else {
                document.getElementById('notificationBadge').style.display = 'none';
            }
        } catch (error) {
            console.error('Erreur chargement notifications:', error);
        }
    },

    renderNotifications(data) {
        const list = document.getElementById('notificationList');
        const notifications = data.notifications || [];
        if (notifications.length === 0) {
            list.innerHTML = '<p class="empty" style="padding:16px; text-align:center; color:#999;">Aucune notification</p>';
            return;
        }
        list.innerHTML = notifications.map(n => `
            <div class="notification-item ${n.is_read ? '' : 'unread'} type-${n.type}" data-id="${n.id}">
                <div class="title">${n.title}</div>
                <div class="message">${n.message}</div>
                <div class="time">${new Date(n.created_at).toLocaleString()}</div>
                ${!n.is_read ? `<button class="mark-read-btn" data-id="${n.id}">Marquer comme lu</button>` : ''}
            </div>
        `).join('');

        // Gérer le clic sur "Marquer comme lu"
        list.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = e.target.dataset.id;
                this.markRead(id);
            });
        });
    },

    toggleDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (this._isOpen) {
            dropdown.style.display = 'none';
            this._isOpen = false;
        } else {
            dropdown.style.display = 'block';
            this._isOpen = true;
            // Recharger pour avoir les dernières notifications
            this.loadNotifications(false);
        }
    },

    closeDropdown() {
        document.getElementById('notificationDropdown').style.display = 'none';
        this._isOpen = false;
    },

    async markRead(id) {
        try {
            await api.markNotificationRead(id);
            this.loadNotifications(false);
        } catch (error) {
            console.error('Erreur marquage lu:', error);
        }
    },

    async markAllRead() {
        try {
            await api.markAllNotificationsRead();
            this.loadNotifications(false);
        } catch (error) {
            console.error('Erreur marquage tout lu:', error);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    notificationsManager.init();
});