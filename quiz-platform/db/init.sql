-- ============================================================
-- Quiz Platform — Database Schema & Seed Data
-- Dijalankan otomatis saat container MySQL pertama kali hidup
-- ============================================================

CREATE DATABASE IF NOT EXISTS quiz_platform;
USE quiz_platform;

-- ------------------------------------------------------------
-- Tabel students
-- Menyimpan data mahasiswa yang akan mengikuti ujian
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    student_id  VARCHAR(20) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(100) UNIQUE,
    password    VARCHAR(255) NOT NULL DEFAULT 'password123',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabel quizzes
-- Menyimpan metadata ujian (judul, mata kuliah, durasi)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quizzes (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    title            VARCHAR(200) NOT NULL,
    subject          VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL DEFAULT 30,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabel questions
-- Menyimpan soal-soal beserta pilihan jawaban dan kunci jawaban
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id             INT PRIMARY KEY AUTO_INCREMENT,
    quiz_id        INT NOT NULL,
    question_text  TEXT NOT NULL,
    option_a       VARCHAR(255) NOT NULL,
    option_b       VARCHAR(255) NOT NULL,
    option_c       VARCHAR(255) NOT NULL,
    option_d       VARCHAR(255) NOT NULL,
    correct_answer CHAR(1) NOT NULL,   -- nilai: 'A', 'B', 'C', atau 'D'
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Tabel submissions
-- Menyimpan hasil pengerjaan ujian oleh mahasiswa
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS submissions (
    id           INT PRIMARY KEY AUTO_INCREMENT,
    student_id   INT NOT NULL,
    quiz_id      INT NOT NULL,
    answers      JSON NOT NULL,            -- {"1": "A", "2": "C", ...} (question_id -> jawaban)
    score        FLOAT NOT NULL DEFAULT 0,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by VARCHAR(20),             -- nama node yang memproses, contoh: "quiz-1"
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
);

-- ------------------------------------------------------------
-- Tabel notifications
-- Diisi oleh Notification Service setelah submission diproses
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    message    TEXT NOT NULL,
    is_read    TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id)
);


-- ============================================================
-- SEED DATA
-- ============================================================

-- ------------------------------------------------------------
-- Data mahasiswa (5 akun untuk keperluan testing)
-- Login menggunakan student_id (NIM)
-- ------------------------------------------------------------
INSERT INTO students (student_id, name, email, password) VALUES
    ('2021001', 'Andi Pratama',   'andi@mahasiswa.ac.id',  'password123'),
    ('2021002', 'Budi Santoso',   'budi@mahasiswa.ac.id',  'password123'),
    ('2021003', 'Citra Dewi',     'citra@mahasiswa.ac.id', 'password123'),
    ('2021004', 'Dian Rahayu',    'dian@mahasiswa.ac.id',  'password123'),
    ('2021005', 'Eko Firmansyah', 'eko@mahasiswa.ac.id',   'password123');

-- ------------------------------------------------------------
-- Data ujian (1 ujian untuk testing)
-- ------------------------------------------------------------
INSERT INTO quizzes (title, subject, duration_minutes) VALUES
    ('UTS Sistem Terdistribusi', 'Sistem Terdistribusi', 45);

-- ------------------------------------------------------------
-- Soal-soal ujian (5 soal pilihan ganda)
-- quiz_id = 1 merujuk ke ujian yang baru dibuat di atas
-- ------------------------------------------------------------
INSERT INTO questions (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer) VALUES
(
    1,
    'Apa yang dimaksud dengan sistem terdistribusi?',
    'Sistem yang berjalan pada satu komputer dengan banyak prosesor',
    'Kumpulan komputer independen yang tampak sebagai satu sistem bagi pengguna',
    'Sistem operasi yang mendukung multitasking',
    'Jaringan komputer yang terhubung melalui internet',
    'B'
),
(
    1,
    'Algoritma Bully digunakan untuk keperluan apa dalam sistem terdistribusi?',
    'Mengatur pengiriman pesan antar node',
    'Menyinkronkan waktu di semua node',
    'Memilih koordinator (leader) di antara node-node yang ada',
    'Membagi beban kerja secara merata ke semua node',
    'C'
),
(
    1,
    'Pada algoritma Ring-based Election, pesan ELECTION diteruskan ke mana?',
    'Ke semua node secara broadcast',
    'Ke node dengan ID terbesar',
    'Ke node tetangga sebelah kiri',
    'Ke node tetangga sebelah kanan',
    'D'
),
(
    1,
    'Apa fungsi utama RabbitMQ dalam arsitektur sistem terdistribusi?',
    'Menyimpan data secara permanen',
    'Menjadi message broker untuk komunikasi asynchronous antar service',
    'Mengatur load balancing request HTTP',
    'Menjalankan proses election antar node',
    'B'
),
(
    1,
    'Dalam konteks load balancing, apa yang dimaksud dengan strategi round-robin?',
    'Request selalu diteruskan ke node dengan beban paling ringan',
    'Request diteruskan ke node secara acak',
    'Request diteruskan ke node secara bergantian dan berurutan',
    'Request selalu diteruskan ke node pertama yang tersedia',
    'C'
);
