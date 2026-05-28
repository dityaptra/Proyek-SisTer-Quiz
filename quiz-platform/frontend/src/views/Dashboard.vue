<template>
  <div class="page">
    <div class="container">
      <div class="welcome">
        <h2>Selamat datang, {{ student.name }}</h2>
        <p>NIM: {{ student.student_id }}</p>
      </div>

      <div class="section">
        <h3>Ujian Tersedia</h3>
        <div v-if="loadingQuizzes" class="loading">Memuat daftar ujian...</div>
        <div v-else-if="quizzes.length === 0" class="empty">Belum ada ujian tersedia.</div>
        <div v-else class="quiz-grid">
          <div v-for="quiz in quizzes" :key="quiz.id" class="quiz-card">
            <div class="quiz-info">
              <h4>{{ quiz.title }}</h4>
              <p class="subject">{{ quiz.subject }}</p>
              <p class="duration">Durasi: {{ quiz.duration_minutes }} menit</p>
            </div>
            <div class="quiz-action">
              <span v-if="submittedQuizIds.includes(quiz.id)" class="badge-done">Selesai</span>
              <button v-else @click="startQuiz(quiz.id)" class="btn-start">Mulai Ujian</button>
            </div>
          </div>
        </div>
      </div>

      <div class="section">
        <h3>Riwayat Ujian</h3>
        <div v-if="loadingHistory" class="loading">Memuat riwayat...</div>
        <div v-else-if="submissions.length === 0" class="empty">Belum ada riwayat ujian.</div>
        <table v-else class="history-table">
          <thead>
            <tr>
              <th>Ujian</th><th>Mata Kuliah</th><th>Skor</th><th>Dikumpulkan</th><th>Detail</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in submissions" :key="s.id">
              <td>{{ s.quiz_title }}</td>
              <td>{{ s.subject }}</td>
              <td>
                <span :class="scoreClass(s.score)">{{ s.score }}</span>
              </td>
              <td>{{ formatDate(s.submitted_at) }}</td>
              <td>
                <router-link :to="`/result/${s.id}`" class="btn-detail">Lihat</router-link>
              </td>
            </tr>
          </tbody>
        </table>
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
      quizzes: [],
      submissions: [],
      loadingQuizzes: true,
      loadingHistory: true
    }
  },
  computed: {
    submittedQuizIds() {
      return this.submissions.map(s => s.quiz_id)
    }
  },
  async mounted() {
    await Promise.all([this.fetchQuizzes(), this.fetchHistory()])
  },
  methods: {
    async fetchQuizzes() {
      try {
        const res = await axios.get('/api/quizzes')
        this.quizzes = res.data.quizzes
      } finally { this.loadingQuizzes = false }
    },
    async fetchHistory() {
      try {
        const res = await axios.get(`/api/students/${this.student.id}/submissions`)
        this.submissions = res.data.submissions
      } finally { this.loadingHistory = false }
    },
    startQuiz(quizId) {
      this.$router.push(`/quiz/${quizId}`)
    },
    scoreClass(score) {
      if (score >= 80) return 'score-high'
      if (score >= 60) return 'score-mid'
      return 'score-low'
    },
    formatDate(dt) {
      return new Date(dt).toLocaleString('id-ID')
    }
  }
}
</script>

<style scoped>
.page { padding: 28px 16px; }
.container { max-width: 900px; margin: 0 auto; }
.welcome { margin-bottom: 28px; }
.welcome h2 { font-size: 22px; color: #2c3e50; }
.welcome p { color: #7f8c8d; margin-top: 4px; }
.section { margin-bottom: 36px; }
.section h3 { font-size: 17px; font-weight: 600; color: #2c3e50; margin-bottom: 16px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }
.quiz-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.quiz-card {
  background: white; border-radius: 10px;
  padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  display: flex; justify-content: space-between; align-items: center;
}
.quiz-info h4 { font-size: 15px; color: #2c3e50; margin-bottom: 6px; }
.subject { font-size: 13px; color: #3498db; }
.duration { font-size: 12px; color: #95a5a6; margin-top: 4px; }
.btn-start {
  background: #3498db; color: white;
  border: none; border-radius: 6px;
  padding: 8px 16px; cursor: pointer; font-size: 13px; white-space: nowrap;
}
.btn-start:hover { background: #2980b9; }
.badge-done {
  background: #e8f5e9; color: #27ae60;
  border-radius: 20px; padding: 6px 14px; font-size: 12px; font-weight: 600;
}
.history-table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
.history-table th { background: #f8f9fa; padding: 12px 16px; text-align: left; font-size: 13px; color: #666; }
.history-table td { padding: 12px 16px; font-size: 14px; border-top: 1px solid #f1f1f1; }
.score-high { color: #27ae60; font-weight: 700; }
.score-mid  { color: #f39c12; font-weight: 700; }
.score-low  { color: #e74c3c; font-weight: 700; }
.btn-detail { color: #3498db; text-decoration: none; font-size: 13px; }
.loading, .empty { color: #95a5a6; font-size: 14px; padding: 20px 0; }
</style>
