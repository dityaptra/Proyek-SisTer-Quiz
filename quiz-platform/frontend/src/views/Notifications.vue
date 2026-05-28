<template>
  <div class="page">
    <div class="container">
      <h2>Notifikasi</h2>
      <div v-if="loading" class="loading">Memuat notifikasi...</div>
      <div v-else-if="notifications.length === 0" class="empty">
        Belum ada notifikasi.
      </div>
      <div v-else>
        <div
          v-for="n in notifications"
          :key="n.id"
          class="notif-item"
          :class="{ unread: !n.is_read }"
        >
          <div class="notif-icon">📋</div>
          <div class="notif-content">
            <p>{{ n.message }}</p>
            <span class="notif-time">{{ formatDate(n.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      student: JSON.parse(localStorage.getItem('student')),
      notifications: [],
      loading: true
    }
  },
  async mounted() {
    await this.fetchNotifications()
    // Tandai semua sudah dibaca
    await axios.post(`/api/notifications/${this.student.id}/read`).catch(() => {})
  },
  methods: {
    async fetchNotifications() {
      try {
        const res = await axios.get(`/api/notifications/${this.student.id}`)
        this.notifications = res.data.notifications
      } finally {
        this.loading = false
      }
    },
    formatDate(dt) {
      return new Date(dt).toLocaleString('id-ID')
    }
  }
}
</script>

<style scoped>
.page { padding: 28px 16px; }
.container { max-width: 700px; margin: 0 auto; }
h2 { font-size: 20px; color: #2c3e50; margin-bottom: 20px; }
.notif-item {
  background: white; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 12px;
  display: flex; gap: 16px; align-items: flex-start;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  border-left: 4px solid #ecf0f1;
}
.notif-item.unread { border-left-color: #3498db; background: #eaf4fd; }
.notif-icon { font-size: 22px; flex-shrink: 0; }
.notif-content p { font-size: 14px; color: #2c3e50; line-height: 1.6; }
.notif-time { font-size: 12px; color: #95a5a6; margin-top: 4px; display: block; }
.loading, .empty { color: #95a5a6; font-size: 14px; padding: 40px 0; text-align: center; }
</style>
