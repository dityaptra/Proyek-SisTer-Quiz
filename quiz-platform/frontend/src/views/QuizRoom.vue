<template>
  <div class="quiz-page">
    <div v-if="loading" class="loading">Memuat soal ujian...</div>
    <div v-else-if="error" class="alert-error">{{ error }}</div>
    <div v-else class="quiz-layout">

      <!-- Sidebar kiri: info ujian + grid nomor soal -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h3>{{ quiz.title }}</h3>
          <p>{{ quiz.subject }}</p>
        </div>

        <div class="timer-box" :class="{ warning: timeLeft <= 60 }">
          <span class="timer-label">Sisa Waktu</span>
          <span class="timer-value">{{ formatTime(timeLeft) }}</span>
        </div>

        <div class="progress-info">
          <span>{{ answeredCount }}/{{ questions.length }} terjawab</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </div>

        <div class="question-grid">
          <button
            v-for="(q, idx) in questions"
            :key="q.id"
            class="grid-btn"
            :class="{
              active:    currentIndex === idx,
              answered:  answers[q.id],
              unanswered: !answers[q.id] && currentIndex !== idx
            }"
            @click="goTo(idx)"
          >
            {{ idx + 1 }}
          </button>
        </div>

        <div class="legend">
          <span class="leg-item"><span class="leg-dot answered"></span> Terjawab</span>
          <span class="leg-item"><span class="leg-dot active"></span> Aktif</span>
          <span class="leg-item"><span class="leg-dot unanswered"></span> Belum</span>
        </div>

        <button
          @click="confirmSubmit"
          :disabled="submitted || submitting"
          class="btn-submit"
        >
          {{ submitting ? 'Mengumpulkan...' : 'Kumpulkan Jawaban' }}
        </button>
      </aside>

      <!-- Area soal utama -->
      <main class="question-area">
        <div class="question-card">
          <div class="question-header">
            <span class="q-number">Soal {{ currentIndex + 1 }} dari {{ questions.length }}</span>
          </div>

          <p class="question-text">{{ currentQuestion.question_text }}</p>

          <div class="options">
            <label
              v-for="opt in ['A','B','C','D']"
              :key="opt"
              class="option"
              :class="{ selected: answers[currentQuestion.id] === opt }"
            >
              <input
                type="radio"
                :name="`q${currentQuestion.id}`"
                :value="opt"
                v-model="answers[currentQuestion.id]"
                :disabled="submitted"
              />
              <span class="opt-label">{{ opt }}</span>
              <span class="opt-text">{{ currentQuestion[`option_${opt.toLowerCase()}`] }}</span>
            </label>
          </div>
        </div>

        <!-- Navigasi bawah -->
        <div class="nav-buttons">
          <button
            @click="prev"
            :disabled="currentIndex === 0"
            class="btn-nav"
          >
            ← Sebelumnya
          </button>

          <span class="nav-counter">{{ currentIndex + 1 }} / {{ questions.length }}</span>

          <button
            v-if="currentIndex < questions.length - 1"
            @click="next"
            class="btn-nav btn-next"
          >
            Selanjutnya →
          </button>
          <button
            v-else
            @click="confirmSubmit"
            :disabled="submitted || submitting"
            class="btn-nav btn-finish"
          >
            Selesai & Kumpulkan
          </button>
        </div>

        <div v-if="submitError" class="alert-error" style="margin-top:16px">{{ submitError }}</div>
      </main>

    </div>

    <!-- Modal konfirmasi submit -->
    <div v-if="showConfirm" class="modal-overlay">
      <div class="modal">
        <h3>Kumpulkan Jawaban?</h3>
        <p>
          Kamu baru menjawab <strong>{{ answeredCount }}</strong> dari
          <strong>{{ questions.length }}</strong> soal.
        </p>
        <p v-if="answeredCount < questions.length" class="warn-text">
          ⚠️ Masih ada {{ questions.length - answeredCount }} soal yang belum dijawab.
        </p>
        <p class="modal-note">Jawaban tidak dapat diubah setelah dikumpulkan.</p>
        <div class="modal-actions">
          <button @click="showConfirm = false" class="btn-cancel">Kembali</button>
          <button @click="submitQuiz" class="btn-confirm">Ya, Kumpulkan</button>
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
      student:      JSON.parse(localStorage.getItem('student')),
      quiz:         null,
      questions:    [],
      answers:      {},
      currentIndex: 0,
      loading:      true,
      error:        '',
      submitError:  '',
      submitting:   false,
      submitted:    false,
      showConfirm:  false,
      timeLeft:     0,
      timerInterval: null
    }
  },
  computed: {
    currentQuestion() {
      return this.questions[this.currentIndex] || {}
    },
    answeredCount() {
      return Object.keys(this.answers).length
    },
    progressPercent() {
      if (!this.questions.length) return 0
      return Math.round((this.answeredCount / this.questions.length) * 100)
    }
  },
  async mounted() {
    await this.fetchQuiz()
  },
  beforeUnmount() {
    clearInterval(this.timerInterval)
  },
  methods: {
    async fetchQuiz() {
      try {
        const res = await axios.get(`/api/quizzes/${this.$route.params.id}`)
        this.quiz      = res.data.quiz
        this.questions = res.data.questions
        this.timeLeft  = this.quiz.duration_minutes * 60
        this.startTimer()
      } catch {
        this.error = 'Gagal memuat soal ujian.'
      } finally {
        this.loading = false
      }
    },
    startTimer() {
      this.timerInterval = setInterval(() => {
        this.timeLeft--
        if (this.timeLeft <= 0) {
          clearInterval(this.timerInterval)
          this.submitQuiz()
        }
      }, 1000)
    },
    formatTime(seconds) {
      const m = Math.floor(seconds / 60).toString().padStart(2, '0')
      const s = (seconds % 60).toString().padStart(2, '0')
      return `${m}:${s}`
    },
    goTo(idx) {
      this.currentIndex = idx
    },
    prev() {
      if (this.currentIndex > 0) this.currentIndex--
    },
    next() {
      if (this.currentIndex < this.questions.length - 1) this.currentIndex++
    },
    confirmSubmit() {
      this.showConfirm = true
    },
    async submitQuiz() {
      this.showConfirm = false
      if (this.submitting || this.submitted) return
      this.submitError = ''
      this.submitting  = true
      clearInterval(this.timerInterval)

      try {
        const res = await axios.post(
          `/api/quizzes/${this.$route.params.id}/submit`,
          { student_id: this.student.id, answers: this.answers }
        )
        this.submitted = true
        this.$router.push(`/result/${res.data.submission_id}`)
      } catch (e) {
        this.submitError = e.response?.data?.error || 'Gagal mengumpulkan jawaban. Coba lagi.'
        this.submitting  = false
      }
    }
  }
}
</script>

<style scoped>
.quiz-page { min-height: 100vh; background: #f0f2f5; }

.quiz-layout {
  display: flex;
  min-height: calc(100vh - 56px);
}

/* ── Sidebar ── */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #2c3e50;
  color: white;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 56px;
  height: calc(100vh - 56px);
  overflow-y: auto;
}

.sidebar-header h3 { font-size: 14px; font-weight: 600; line-height: 1.4; }
.sidebar-header p  { font-size: 12px; color: #95a5a6; margin-top: 4px; }

.timer-box {
  background: #34495e;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  border: 2px solid transparent;
  transition: border-color 0.3s;
}
.timer-box.warning { border-color: #e74c3c; background: #3d1f1f; }
.timer-label { display: block; font-size: 11px; color: #95a5a6; margin-bottom: 4px; }
.timer-value { font-size: 26px; font-weight: 800; font-variant-numeric: tabular-nums; }
.timer-box.warning .timer-value { color: #e74c3c; }

.progress-info { font-size: 12px; color: #bdc3c7; }
.progress-bar  { background: #34495e; border-radius: 4px; height: 6px; margin-top: 6px; }
.progress-fill { background: #27ae60; border-radius: 4px; height: 100%; transition: width 0.3s; }

.question-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}
.grid-btn {
  aspect-ratio: 1;
  border-radius: 6px;
  border: none;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  background: #34495e;
  color: #bdc3c7;
}
.grid-btn.answered  { background: #27ae60; color: white; }
.grid-btn.active    { background: #3498db; color: white; transform: scale(1.1); }
.grid-btn:hover     { opacity: 0.85; }

.legend { display: flex; flex-direction: column; gap: 6px; }
.leg-item { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #95a5a6; }
.leg-dot {
  width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0;
}
.leg-dot.answered  { background: #27ae60; }
.leg-dot.active    { background: #3498db; }
.leg-dot.unanswered { background: #34495e; border: 1px solid #4a6278; }

.btn-submit {
  background: #e74c3c; color: white;
  border: none; border-radius: 8px;
  padding: 12px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
  margin-top: auto;
}
.btn-submit:hover:not(:disabled) { background: #c0392b; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Question Area ── */
.question-area {
  flex: 1;
  padding: 28px 32px;
  max-width: 780px;
}

.question-card {
  background: white;
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  margin-bottom: 20px;
}

.question-header { margin-bottom: 16px; }
.q-number {
  font-size: 12px; font-weight: 600;
  color: #3498db; text-transform: uppercase; letter-spacing: 0.05em;
}

.question-text {
  font-size: 17px; color: #2c3e50;
  line-height: 1.7; margin-bottom: 24px; font-weight: 500;
}

.options { display: flex; flex-direction: column; gap: 12px; }
.option {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px; border-radius: 10px;
  border: 2px solid #ecf0f1; cursor: pointer;
  transition: all 0.15s; background: #fafafa;
}
.option:hover   { border-color: #3498db; background: #eaf4fd; }
.option.selected { border-color: #3498db; background: #eaf4fd; }
.option input[type="radio"] { display: none; }
.opt-label {
  background: #ecf0f1; border-radius: 6px;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; flex-shrink: 0;
  transition: all 0.15s;
}
.option.selected .opt-label { background: #3498db; color: white; }
.opt-text { font-size: 15px; color: #2c3e50; line-height: 1.5; }

/* ── Navigasi ── */
.nav-buttons {
  display: flex; align-items: center;
  justify-content: space-between; gap: 12px;
}
.btn-nav {
  padding: 10px 24px; border-radius: 8px;
  border: 2px solid #ddd; background: white;
  font-size: 14px; font-weight: 600; cursor: pointer;
  color: #2c3e50; transition: all 0.15s;
}
.btn-nav:hover:not(:disabled) { border-color: #3498db; color: #3498db; }
.btn-nav:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-nav.btn-next   { border-color: #3498db; color: #3498db; }
.btn-nav.btn-finish { border-color: #27ae60; color: #27ae60; }
.btn-nav.btn-next:hover   { background: #3498db; color: white; }
.btn-nav.btn-finish:hover { background: #27ae60; color: white; }
.nav-counter { font-size: 13px; color: #95a5a6; flex: 1; text-align: center; }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 200;
  min-height: 100vh;
}
.modal {
  background: white; border-radius: 12px;
  padding: 32px; width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.modal h3 { font-size: 18px; color: #2c3e50; margin-bottom: 12px; }
.modal p  { font-size: 14px; color: #555; margin-bottom: 8px; line-height: 1.6; }
.warn-text { color: #e67e22; font-weight: 600; }
.modal-note { font-size: 12px; color: #95a5a6; margin-top: 8px; }
.modal-actions { display: flex; gap: 12px; margin-top: 24px; }
.btn-cancel {
  flex: 1; padding: 10px; border-radius: 8px;
  border: 2px solid #ddd; background: white;
  font-size: 14px; cursor: pointer; color: #555;
}
.btn-cancel:hover { border-color: #999; }
.btn-confirm {
  flex: 1; padding: 10px; border-radius: 8px;
  border: none; background: #e74c3c; color: white;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.btn-confirm:hover { background: #c0392b; }

.alert-error {
  background: #fdecea; color: #c0392b;
  border-radius: 6px; padding: 10px 14px; font-size: 13px;
}
.loading { color: #95a5a6; padding: 60px; text-align: center; }
</style>