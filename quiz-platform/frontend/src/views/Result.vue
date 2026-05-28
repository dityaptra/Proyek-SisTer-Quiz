<template>
  <div class="page">
    <div class="container">
      <div v-if="loading" class="loading">Memuat hasil ujian...</div>
      <div v-else-if="error" class="alert-error">{{ error }}</div>
      <div v-else>
        <!-- Score Card -->
        <div class="score-card" :class="scoreClass">
          <div class="score-circle">
            <span class="score-num">{{ submission.score }}</span>
            <span class="score-label">/100</span>
          </div>
          <div class="score-info">
            <h2>{{ scoreMessage }}</h2>
            <p>{{ quiz.title }}</p>
            <p class="meta">
              Dikumpulkan: {{ formatDate(submission.submitted_at) }} &nbsp;|&nbsp;
              Diproses oleh: <strong>{{ submission.processed_by }}</strong>
            </p>
          </div>
        </div>

        <!-- Review Jawaban -->
        <h3 class="review-title">Review Jawaban</h3>
        <div
          v-for="(q, idx) in questions"
          :key="q.id"
          class="review-card"
          :class="isCorrect(q) ? 'correct' : 'wrong'"
        >
          <div class="review-header">
            <span class="review-num">Soal {{ idx + 1 }}</span>
            <span class="review-status">{{ isCorrect(q) ? '✓ Benar' : '✗ Salah' }}</span>
          </div>
          <p class="review-question">{{ q.question_text }}</p>
          <div class="review-answers">
            <div
              v-for="opt in ['A','B','C','D']"
              :key="opt"
              class="review-opt"
              :class="optClass(q, opt)"
            >
              <span class="opt-label">{{ opt }}</span>
              {{ q[`option_${opt.toLowerCase()}`] }}
            </div>
          </div>
        </div>

        <div class="actions">
          <router-link to="/dashboard" class="btn-back">Kembali ke Dashboard</router-link>
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
      submission: null,
      quiz: null,
      questions: [],
      answers: {},
      loading: true,
      error: ''
    }
  },
  computed: {
    scoreClass() {
      if (!this.submission) return ''
      if (this.submission.score >= 80) return 'high'
      if (this.submission.score >= 60) return 'mid'
      return 'low'
    },
    scoreMessage() {
      if (!this.submission) return ''
      if (this.submission.score >= 80) return 'Luar Biasa!'
      if (this.submission.score >= 60) return 'Cukup Baik'
      return 'Perlu Belajar Lebih Giat'
    }
  },
  async mounted() {
    await this.fetchResult()
  },
  methods: {
    async fetchResult() {
      try {
        const res = await axios.get(`/api/submissions/${this.$route.params.id}`)
        this.submission = res.data.submission
        this.questions = res.data.questions
        this.answers = this.submission.answers || {}

        const qRes = await axios.get(`/api/quizzes/${this.submission.quiz_id}`)
        this.quiz = qRes.data.quiz
      } catch {
        this.error = 'Gagal memuat hasil ujian.'
      } finally {
        this.loading = false
      }
    },
    isCorrect(q) {
      return (this.answers[String(q.id)] || '').toUpperCase() === q.correct_answer.toUpperCase()
    },
    optClass(q, opt) {
      const userAns = (this.answers[String(q.id)] || '').toUpperCase()
      if (opt === q.correct_answer) return 'opt-correct'
      if (opt === userAns && userAns !== q.correct_answer) return 'opt-wrong'
      return ''
    },
    formatDate(dt) {
      return new Date(dt).toLocaleString('id-ID')
    }
  }
}
</script>

<style scoped>
.page { padding: 28px 16px; }
.container { max-width: 760px; margin: 0 auto; }
.score-card {
  border-radius: 12px; padding: 28px 32px;
  display: flex; align-items: center; gap: 28px;
  margin-bottom: 32px; color: white;
}
.score-card.high { background: linear-gradient(135deg, #27ae60, #2ecc71); }
.score-card.mid  { background: linear-gradient(135deg, #f39c12, #e67e22); }
.score-card.low  { background: linear-gradient(135deg, #e74c3c, #c0392b); }
.score-circle {
  min-width: 100px; height: 100px; border-radius: 50%;
  background: rgba(255,255,255,0.25);
  display: flex; align-items: center; justify-content: center; flex-direction: column;
}
.score-num { font-size: 32px; font-weight: 800; line-height: 1; }
.score-label { font-size: 14px; opacity: 0.8; }
.score-info h2 { font-size: 22px; margin-bottom: 6px; }
.score-info p { opacity: 0.9; font-size: 14px; margin-top: 4px; }
.meta { font-size: 12px !important; opacity: 0.75 !important; }
.review-title { font-size: 17px; font-weight: 600; color: #2c3e50; margin-bottom: 16px; }
.review-card {
  background: white; border-radius: 10px;
  padding: 18px 22px; margin-bottom: 14px;
  border-left: 4px solid #ecf0f1;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
.review-card.correct { border-left-color: #27ae60; }
.review-card.wrong   { border-left-color: #e74c3c; }
.review-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
.review-num { font-size: 12px; color: #95a5a6; }
.review-status { font-size: 13px; font-weight: 600; }
.correct .review-status { color: #27ae60; }
.wrong   .review-status { color: #e74c3c; }
.review-question { font-size: 14px; color: #2c3e50; margin-bottom: 14px; line-height: 1.6; }
.review-answers { display: flex; flex-direction: column; gap: 8px; }
.review-opt {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 6px; font-size: 13px;
  background: #f8f9fa;
}
.review-opt.opt-correct { background: #eafaf1; color: #27ae60; font-weight: 600; }
.review-opt.opt-wrong   { background: #fdecea; color: #e74c3c; font-weight: 600; text-decoration: line-through; }
.opt-label {
  background: #ecf0f1; border-radius: 4px;
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 12px; flex-shrink: 0;
}
.opt-correct .opt-label { background: #27ae60; color: white; }
.opt-wrong   .opt-label { background: #e74c3c; color: white; }
.actions { text-align: center; margin-top: 28px; padding-bottom: 40px; }
.btn-back {
  background: #2c3e50; color: white;
  text-decoration: none; border-radius: 8px;
  padding: 12px 32px; font-size: 14px;
}
.alert-error { background: #fdecea; color: #c0392b; border-radius: 6px; padding: 10px 14px; font-size: 13px; }
.loading { color: #95a5a6; padding: 40px; text-align: center; }
</style>
