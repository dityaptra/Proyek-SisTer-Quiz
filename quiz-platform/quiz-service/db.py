import os
import time
import mysql.connector
from mysql.connector import pooling

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "mysql"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "quiz_platform"),
}

_pool = None

def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    for attempt in range(1, 16):
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="quiz_pool",
                pool_size=5,
                **DB_CONFIG
            )
            print(f"[db] MySQL connection pool created (attempt {attempt})", flush=True)
            return _pool
        except Exception as e:
            print(f"[db] MySQL not ready yet ({attempt}/15): {e}", flush=True)
            time.sleep(3)
    raise RuntimeError("[db] Could not connect to MySQL after multiple retries")

def get_connection():
    return _get_pool().get_connection()

# ─────────────────────────────────────────────
# Query: Students
# ─────────────────────────────────────────────

def get_student_by_student_id(student_id: str):
    """Cari mahasiswa berdasarkan NIM."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM students WHERE student_id = %s",
        (student_id,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_student_by_email(email: str):
    """Cari mahasiswa berdasarkan email. Digunakan saat login."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM students WHERE email = %s",
        (email,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_student_by_id(id: int):
    """Cari mahasiswa berdasarkan primary key id."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


# ─────────────────────────────────────────────
# Query: Quizzes
# ─────────────────────────────────────────────

def get_all_quizzes():
    """Ambil semua quiz yang tersedia. Ditampilkan di halaman dashboard."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM quizzes ORDER BY created_at DESC")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def get_quiz_by_id(quiz_id: int):
    """Ambil detail satu quiz berdasarkan id-nya."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_questions_by_quiz_id(quiz_id: int, include_answer=False):
    """
    Ambil semua soal untuk quiz tertentu.
    include_answer=False saat dikirim ke mahasiswa (sembunyikan kunci jawaban).
    include_answer=True saat menampilkan hasil (tampilkan kunci jawaban).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if include_answer:
        cursor.execute(
            "SELECT * FROM questions WHERE quiz_id = %s ORDER BY id",
            (quiz_id,)
        )
    else:
        # Sembunyikan kolom correct_answer saat ujian berlangsung
        cursor.execute(
            """SELECT id, quiz_id, question_text,
                      option_a, option_b, option_c, option_d
               FROM questions WHERE quiz_id = %s ORDER BY id""",
            (quiz_id,)
        )

    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


# ─────────────────────────────────────────────
# Query: Submissions
# ─────────────────────────────────────────────

def save_submission(student_id: int, quiz_id: int, answers: dict,
                    score: float, processed_by: str):
    """
    Simpan hasil submission ke database.
    Dipanggil hanya oleh node leader setelah skor dihitung.
    answers disimpan dalam format JSON: {"question_id": "jawaban", ...}
    """
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO submissions (student_id, quiz_id, answers, score, processed_by)
           VALUES (%s, %s, %s, %s, %s)""",
        (student_id, quiz_id, json.dumps(answers), score, processed_by)
    )
    conn.commit()
    submission_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return submission_id

def get_submission_by_id(submission_id: int):
    """Ambil detail satu submission berdasarkan id-nya."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM submissions WHERE id = %s", (submission_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_submissions_by_student(student_id: int):
    """Ambil riwayat semua submission milik satu mahasiswa."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT s.*, q.title AS quiz_title, q.subject
           FROM submissions s
           JOIN quizzes q ON s.quiz_id = q.id
           WHERE s.student_id = %s
           ORDER BY s.submitted_at DESC""",
        (student_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def check_existing_submission(student_id: int, quiz_id: int):
    """
    Cek apakah mahasiswa sudah pernah submit quiz ini.
    Mencegah submission ganda (idempotent check).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM submissions WHERE student_id = %s AND quiz_id = %s",
        (student_id, quiz_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


# ─────────────────────────────────────────────
# Query: Notifications
# ─────────────────────────────────────────────

def save_notification(student_id: int, message: str):
    """
    Simpan notifikasi baru untuk mahasiswa.
    Dipanggil oleh Notification Service setelah mengonsumsi pesan dari RabbitMQ.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (student_id, message) VALUES (%s, %s)",
        (student_id, message)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_notifications_by_student(student_id: int):
    """Ambil semua notifikasi milik satu mahasiswa, terbaru di atas."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM notifications WHERE student_id = %s
           ORDER BY created_at DESC""",
        (student_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def mark_notifications_read(student_id: int):
    """Tandai semua notifikasi milik mahasiswa sebagai sudah dibaca."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read = 1 WHERE student_id = %s",
        (student_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
