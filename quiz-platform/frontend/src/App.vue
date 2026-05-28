<template>
  <div id="app">
    <nav v-if="student" class="navbar">
      <div class="nav-brand">Quiz Platform</div>
      <div class="nav-links">
        <router-link to="/dashboard">Dashboard</router-link>
        <router-link to="/notifications" class="notif-link">
          Notifikasi
          <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
        </router-link>
        <span class="nav-user">{{ student.name }}</span>
        <button @click="logout" class="btn-logout">Keluar</button>
      </div>
    </nav>
    <main :class="{ 'with-nav': student }">
      <router-view />
    </main>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      student: null,
      unreadCount: 0,
      notifInterval: null
    }
  },
  mounted() {
    const stored = localStorage.getItem('student')
    if (stored) {
      this.student = JSON.parse(stored)
      this.fetchUnreadCount()
      this.notifInterval = setInterval(this.fetchUnreadCount, 15000)
    }
  },
  watch: {
    '$route'() {
      const stored = localStorage.getItem('student')
      this.student = stored ? JSON.parse(stored) : null
      if (this.student) this.fetchUnreadCount()
    }
  },
  methods: {
    async fetchUnreadCount() {
      if (!this.student) return
      try {
        const res = await axios.get(`/api/notifications/${this.student.id}`)
        this.unreadCount = res.data.notifications.filter(n => !n.is_read).length
      } catch {}
    },
    logout() {
      localStorage.removeItem('student')
      this.student = null
      clearInterval(this.notifInterval)
      this.$router.push('/')
    }
  }
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #f5f6fa; color: #2d3436; }

.navbar {
  background: #2c3e50;
  color: white;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
}
.nav-brand { font-weight: 700; font-size: 18px; }
.nav-links { display: flex; align-items: center; gap: 20px; }
.nav-links a { color: #ecf0f1; text-decoration: none; font-size: 14px; }
.nav-links a:hover { color: #3498db; }
.nav-user { font-size: 14px; color: #bdc3c7; }
.notif-link { position: relative; }
.badge {
  background: #e74c3c; color: white;
  border-radius: 50%; width: 18px; height: 18px;
  font-size: 11px; display: inline-flex;
  align-items: center; justify-content: center;
  position: absolute; top: -8px; right: -10px;
}
.btn-logout {
  background: #e74c3c; color: white;
  border: none; border-radius: 6px;
  padding: 6px 14px; cursor: pointer; font-size: 13px;
}
.btn-logout:hover { background: #c0392b; }
main { min-height: 100vh; }
main.with-nav { padding-top: 56px; }
</style>
