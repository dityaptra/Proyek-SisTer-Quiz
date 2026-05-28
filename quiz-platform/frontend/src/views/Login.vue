<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>Quiz Platform</h1>
        <p>Sistem Ujian Online Mahasiswa</p>
      </div>
      <form @submit.prevent="login">
        <div class="form-group">
          <label>Email</label>
          <input
            v-model="email"
            type="email"
            placeholder="contoh@mahasiswa.ac.id"
            :disabled="loading"
            autofocus
          />
        </div>
        <div class="form-group">
          <label>Password</label>
          <div class="input-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Masukkan password"
              :disabled="loading"
            />
            <button type="button" class="toggle-pw" @click="showPassword = !showPassword">
              {{ showPassword ? 'Sembunyikan' : 'Tampilkan' }}
            </button>
          </div>
        </div>
        <div v-if="error" class="alert-error">{{ error }}</div>
        <button type="submit" :disabled="loading" class="btn-login">
          {{ loading ? 'Memproses...' : 'Masuk' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      email: '',
      password: '',
      showPassword: false,
      error: '',
      loading: false,
      accounts: [
        { email: 'andi@mahasiswa.ac.id',  password: 'password123' },
        { email: 'budi@mahasiswa.ac.id',  password: 'password123' },
        { email: 'citra@mahasiswa.ac.id', password: 'password123' },
        { email: 'dian@mahasiswa.ac.id',  password: 'password123' },
        { email: 'eko@mahasiswa.ac.id',   password: 'password123' },
      ]
    }
  },
  methods: {
    async login() {
      this.error = ''
      if (!this.email.trim() || !this.password.trim()) {
        this.error = 'Email dan password tidak boleh kosong'
        return
      }
      this.loading = true
      try {
        const res = await axios.post('/api/students/login', {
          email:    this.email.trim(),
          password: this.password.trim()
        })
        localStorage.setItem('student', JSON.stringify(res.data.student))
        this.$router.push('/dashboard')
      } catch (e) {
        this.error = e.response?.data?.error || 'Login gagal, coba lagi'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: flex;
  align-items: center; justify-content: center;
  background: linear-gradient(135deg, #2c3e50, #3498db);
}
.login-card {
  background: white; border-radius: 12px;
  padding: 40px; width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.login-header { text-align: center; margin-bottom: 28px; }
.login-header h1 { font-size: 26px; color: #2c3e50; }
.login-header p { color: #7f8c8d; margin-top: 6px; font-size: 14px; }
.form-group { margin-bottom: 18px; }
label { display: block; font-size: 13px; font-weight: 600; color: #555; margin-bottom: 8px; }
input {
  width: 100%; padding: 10px 14px;
  border: 1.5px solid #ddd; border-radius: 8px;
  font-size: 15px; outline: none; transition: border 0.2s;
}
input:focus { border-color: #3498db; }
.input-wrap { position: relative; }
.input-wrap input { padding-right: 110px; }
.toggle-pw {
  position: absolute; right: 10px; top: 50%;
  transform: translateY(-50%);
  background: none; border: none; color: #3498db;
  font-size: 12px; cursor: pointer; padding: 4px;
}
.alert-error {
  background: #fdecea; color: #c0392b;
  border-radius: 6px; padding: 10px 14px;
  font-size: 13px; margin-bottom: 16px;
}
.btn-login {
  width: 100%; padding: 12px;
  background: #3498db; color: white;
  border: none; border-radius: 8px;
  font-size: 15px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.btn-login:hover:not(:disabled) { background: #2980b9; }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }
.hint {
  margin-top: 20px; padding-top: 16px;
  border-top: 1px solid #ecf0f1;
}
.hint p { font-size: 12px; color: #95a5a6; margin-bottom: 8px; }
.hint table { width: 100%; border-collapse: collapse; font-size: 12px; }
.hint th { text-align: left; color: #7f8c8d; padding: 4px 6px; font-weight: 600; }
.hint td { padding: 4px 6px; color: #555; border-top: 1px solid #f5f5f5; }
</style>