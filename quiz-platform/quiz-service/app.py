# app.py
# Quiz Service — service utama platform ujian mahasiswa.
# Merupakan ekstensi dari payment_service.py dan order_service.py
# pada demo dist-system, dengan domain diganti dari payment menjadi quiz/assessment.
#
# Perubahan utama dari demo:
# - Bully Algorithm diganti dengan Ring-based Election (ring_election.py)
# - In-memory storage diganti dengan MySQL (db.py)
# - Domain payment diganti dengan domain quiz/assessment
# - Ditambahkan integrasi RabbitMQ untuk notifikasi async

import os
import json
import time
import threading
import logging

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

import db
import ring_election as election

# ─────────────────────────────────────────────
# Inisialisasi Flask
# ─────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # izinkan request dari Vue frontend

log_werkzeug = logging.getLogger("werkzeug")
log_werkzeug.setLevel(logging.ERROR)

# Konfigurasi RabbitMQ untuk publish pesan notifikasi setelah submission
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
NOTIF_QUEUE = os.getenv("NOTIF_QUEUE", "quiz.submission.result")

NODE_NAME = election.NODE_NAME
NODE_ID   = election.NODE_ID

def log(msg: str):
    print(f"[{NODE_NAME} id={NODE_ID}] {msg}", flush=True)


# ─────────────────────────────────────────────
# Helper: RPC Call (diadopsi dari order_service.py demo)
# ─────────────────────────────────────────────
def rpc_call(url: str, method: str, params: dict, timeout: float = 2.0):
    """
    Kirim RPC call ke node lain via HTTP POST ke endpoint /rpc.
    Pola ini sama persis dengan rpc_call() di demo payment_service.py.
    """
    r = requests.post(
        f"{url}/rpc",
        json={"method": method, "params": params},
        timeout=timeout
    )
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────
# Helper: Publish ke RabbitMQ
# Diadopsi dari messaging/producer.py di demo
# ─────────────────────────────────────────────
def publish_notification(payload: dict):
    """
    Publish pesan ke RabbitMQ secara asynchronous setelah submission diproses.
    Notification Service yang akan mengonsumsi pesan ini.
    Pola ini diadopsi dari producer.py di demo messaging/.
    """
    try:
        import pika
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBIT_HOST, heartbeat=10)
        )
        ch = conn.channel()
        ch.queue_declare(queue=NOTIF_QUEUE, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=NOTIF_QUEUE,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        conn.close()
        log(f"Published notification to RabbitMQ for student_id={payload.get('student_id')}")
    except Exception as e:
        log(f"Failed to publish to RabbitMQ: {e}")


# ─────────────────────────────────────────────
# Helper: Hitung Skor
# ─────────────────────────────────────────────
def calculate_score(quiz_id: int, answers: dict) -> float:
    """
    Hitung skor berdasarkan jawaban mahasiswa.
    answers format: {"question_id": "A/B/C/D", ...}
    Skor = (jawaban benar / total soal) * 100
    """
    questions = db.get_questions_by_quiz_id(quiz_id, include_answer=True)
    if not questions:
        return 0.0

    correct = 0
    for q in questions:
        q_id = str(q["id"])
        if answers.get(q_id, "").upper() == q["correct_answer"].upper():
            correct += 1

    return round((correct / len(questions)) * 100, 2)


# ─────────────────────────────────────────────
# Helper: Proses Submission (hanya dijalankan oleh leader)
# ─────────────────────────────────────────────
def process_submission(student_id: int, quiz_id: int, answers: dict) -> dict:
    """
    Proses submission ujian: hitung skor, simpan ke DB, publish ke RabbitMQ.
    Fungsi ini hanya boleh dipanggil oleh node leader,
    sama seperti pola 'pay' di payment_service.py demo yang hanya diproses leader.
    """
    # Cek apakah mahasiswa sudah pernah submit quiz ini
    existing = db.check_existing_submission(student_id, quiz_id)
    if existing:
        log(f"Duplicate submission blocked: student={student_id} quiz={quiz_id}")
        return {
            "submission_id": existing["id"],
            "score": float(existing["score"]),
            "message": "Kamu sudah pernah mengerjakan ujian ini.",
            "processed_by": existing["processed_by"]
        }

    # Ambil data quiz untuk validasi
    quiz = db.get_quiz_by_id(quiz_id)
    if not quiz:
        return {"error": "Quiz tidak ditemukan"}

    # Hitung skor
    score = calculate_score(quiz_id, answers)
    log(f"Calculated score={score} for student={student_id} quiz={quiz_id}")

    # Simpan ke MySQL
    submission_id = db.save_submission(
        student_id=student_id,
        quiz_id=quiz_id,
        answers=answers,
        score=score,
        processed_by=NODE_NAME
    )

    # Ambil data mahasiswa untuk pesan notifikasi
    student = db.get_student_by_id(student_id)
    student_name = student["name"] if student else f"Student {student_id}"

    result = {
        "submission_id": submission_id,
        "score": score,
        "message": f"Ujian berhasil dikumpulkan. Skor kamu: {score}",
        "processed_by": NODE_NAME
    }

    # Publish ke RabbitMQ secara asynchronous
    # Tidak perlu menunggu notifikasi selesai sebelum mengembalikan response
    notif_payload = {
        "student_id":   student_id,
        "student_name": student_name,
        "quiz_id":      quiz_id,
        "quiz_title":   quiz["title"],
        "submission_id": submission_id,
        "score":        score
    }
    threading.Thread(
        target=publish_notification,
        args=(notif_payload,),
        daemon=True
    ).start()

    return result


# ═══════════════════════════════════════════════════════════════
# ENDPOINT: Ring Election
# Mengadopsi pola dari /rpc di payment_service.py demo,
# tapi dipisah menjadi endpoint tersendiri agar lebih eksplisit
# ═══════════════════════════════════════════════════════════════

@app.route("/election", methods=["POST"])
def receive_election():
    """
    Terima pesan ELECTION dari tetangga kiri dalam ring.
    Teruskan ke tetangga kanan sesuai logika Ring Election.
    """
    data = request.get_json(force=True, silent=True) or {}
    candidate_id = int(data.get("candidate_id", 0))
    initiator_id = int(data.get("initiator_id", 0))

    threading.Thread(
        target=election.handle_election_message,
        args=(candidate_id, initiator_id),
        daemon=True
    ).start()

    return jsonify({"result": "OK"})

@app.route("/coordinator", methods=["POST"])
def receive_coordinator():
    """
    Terima pengumuman leader baru.
    Semua node memperbarui state leader mereka.
    """
    data = request.get_json(force=True, silent=True) or {}
    new_leader_id  = int(data.get("leader_id", 0))
    new_leader_url = data.get("leader_url", "")

    election.handle_coordinator_message(new_leader_id, new_leader_url)
    return jsonify({"result": "OK"})

@app.route("/heartbeat", methods=["POST"])
def receive_heartbeat():
    """
    Terima heartbeat dari leader.
    Perbarui timestamp last_heartbeat agar monitor_loop tidak memicu election.
    """
    data = request.get_json(force=True, silent=True) or {}
    with election.state_lock:
        election.leader_id    = int(data.get("leader_id", 0))
        election.leader_url   = data.get("leader_url", "")
        election.is_leader    = (election.leader_id == NODE_ID)
        election.last_heartbeat = time.time()
        election.election_in_progress = False
    return jsonify({"result": "OK"})

@app.route("/status", methods=["GET"])
def get_status():
    """
    Kembalikan state node saat ini.
    Berguna untuk debugging dan monitoring siapa leader.
    """
    with election.state_lock:
        return jsonify({
            "node_name":  NODE_NAME,
            "node_id":    NODE_ID,
            "is_leader":  election.is_leader,
            "leader_id":  election.leader_id,
            "leader_url": election.leader_url,
            "election_in_progress": election.election_in_progress,
            "ring_order": election.SORTED_IDS,
            "next_node":  election.get_next_node_id()
        })


# ═══════════════════════════════════════════════════════════════
# ENDPOINT: RPC (Service-to-Service)
# Diadopsi dari endpoint /rpc di payment_service.py demo.
# Node non-leader meneruskan submission ke leader via endpoint ini.
# ═══════════════════════════════════════════════════════════════

@app.route("/rpc", methods=["POST"])
def handle_rpc():
    """
    Endpoint RPC untuk komunikasi antar node.
    Saat node non-leader menerima submit dari frontend,
    ia akan memanggil /rpc di node leader untuk memproses submission.
    Pola ini sama persis dengan endpoint /rpc di payment_service.py demo.
    """
    body   = request.get_json(force=True, silent=True) or {}
    method = body.get("method")
    params = body.get("params") or {}

    # Method: who_is_leader — untuk mengecek siapa leader saat ini
    if method == "who_is_leader":
        with election.state_lock:
            return jsonify({
                "result": {
                    "leader_id":  election.leader_id,
                    "leader_url": election.leader_url,
                    "i_am_leader": election.is_leader
                }
            })

    # Method: process_submission — diteruskan ke leader untuk diproses
    if method == "process_submission":
        with election.state_lock:
            local_is_leader = election.is_leader
            l_id  = election.leader_id
            l_url = election.leader_url

        # Jika node ini bukan leader, kembalikan error NOT_LEADER
        # agar pemanggil tahu harus retry ke leader
        if not local_is_leader:
            return jsonify({
                "error": {
                    "code": "NOT_LEADER",
                    "leader_id":  l_id,
                    "leader_url": l_url
                }
            }), 409

        result = process_submission(
            student_id=int(params["student_id"]),
            quiz_id=int(params["quiz_id"]),
            answers=params["answers"]
        )
        return jsonify({"result": result})

    return jsonify({"error": {"code": "NO_SUCH_METHOD"}}), 400


# ═══════════════════════════════════════════════════════════════
# ENDPOINT: REST API Publik
# Diakses oleh Vue frontend melalui Nginx load balancer
# ═══════════════════════════════════════════════════════════════

@app.route("/api/students/login", methods=["POST"])
def login():
    """Login mahasiswa menggunakan email dan password."""
    body = request.get_json(force=True, silent=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email dan password wajib diisi"}), 400

    student = db.get_student_by_email(email)
    if not student:
        return jsonify({"error": "Email tidak terdaftar"}), 404

    if student["password"] != password:
        return jsonify({"error": "Password salah"}), 401

    # Hapus password dari response sebelum dikirim ke frontend
    student.pop("password", None)

    log(f"Login: {student['name']} ({email})")
    return jsonify({"student": student})


@app.route("/api/quizzes", methods=["GET"])
def get_quizzes():
    """Ambil daftar semua quiz. Ditampilkan di dashboard mahasiswa."""
    quizzes = db.get_all_quizzes()
    return jsonify({"quizzes": quizzes})


@app.route("/api/quizzes/<int:quiz_id>", methods=["GET"])
def get_quiz(quiz_id):
    """
    Ambil detail quiz beserta soal-soalnya.
    Kunci jawaban tidak disertakan saat endpoint ini dipanggil.
    """
    quiz = db.get_quiz_by_id(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz tidak ditemukan"}), 404

    questions = db.get_questions_by_quiz_id(quiz_id, include_answer=False)
    return jsonify({"quiz": quiz, "questions": questions})


@app.route("/api/quizzes/<int:quiz_id>/submit", methods=["POST"])
def submit_quiz(quiz_id):
    """
    Endpoint submit jawaban ujian.
    Ini adalah endpoint paling kompleks karena melibatkan RPC dan leader election.

    Alur:
    1. Validasi input
    2. Cek apakah node ini adalah leader
    3. Jika leader: proses langsung
    4. Jika bukan leader: forward ke leader via RPC (sama dengan pola di demo)
    """
    body = request.get_json(force=True, silent=True) or {}
    student_id = body.get("student_id")
    answers    = body.get("answers", {})

    if not student_id:
        return jsonify({"error": "student_id wajib diisi"}), 400
    if not answers:
        return jsonify({"error": "answers tidak boleh kosong"}), 400

    with election.state_lock:
        local_is_leader = election.is_leader
        l_url = election.leader_url
        l_id  = election.leader_id

    # Jika node ini bukan leader, forward ke leader via RPC
    # Pola ini diadopsi dari try_pay() di order_service.py demo
    if not local_is_leader:
        if not l_url:
            return jsonify({"error": "Belum ada leader, coba beberapa saat lagi"}), 503

        log(f"Not leader, forwarding submission to leader node-{l_id}")
        try:
            resp = rpc_call(l_url, "process_submission", {
                "student_id": student_id,
                "quiz_id":    quiz_id,
                "answers":    answers
            })
            if "error" in resp:
                return jsonify(resp), 500
            return jsonify(resp["result"])
        except Exception as e:
            return jsonify({"error": f"Gagal menghubungi leader: {str(e)}"}), 503

    # Node ini adalah leader, proses langsung
    log(f"I am leader, processing submission: student={student_id} quiz={quiz_id}")
    result = process_submission(
        student_id=int(student_id),
        quiz_id=quiz_id,
        answers=answers
    )
    return jsonify(result)


@app.route("/api/submissions/<int:submission_id>", methods=["GET"])
def get_submission(submission_id):
    """
    Ambil detail hasil submission beserta kunci jawaban.
    Ditampilkan di halaman hasil ujian.
    """
    submission = db.get_submission_by_id(submission_id)
    if not submission:
        return jsonify({"error": "Submission tidak ditemukan"}), 404

    # Sertakan soal beserta kunci jawaban untuk review
    questions = db.get_questions_by_quiz_id(
        submission["quiz_id"], include_answer=True
    )

    # Parse answers dari JSON string jika perlu
    answers = submission["answers"]
    if isinstance(answers, str):
        answers = json.loads(answers)

    return jsonify({
        "submission": {
            **submission,
            "answers": answers,
            "submitted_at": str(submission["submitted_at"])
        },
        "questions": questions
    })


@app.route("/api/students/<int:student_id>/submissions", methods=["GET"])
def get_student_submissions(student_id):
    """Ambil riwayat semua submission milik satu mahasiswa."""
    submissions = db.get_submissions_by_student(student_id)
    # Konversi datetime ke string agar bisa di-serialize ke JSON
    for s in submissions:
        s["submitted_at"] = str(s["submitted_at"])
    return jsonify({"submissions": submissions})


@app.route("/api/notifications/<int:student_id>", methods=["GET"])
def get_notifications(student_id):
    """Ambil semua notifikasi milik mahasiswa."""
    notifications = db.get_notifications_by_student(student_id)
    for n in notifications:
        n["created_at"] = str(n["created_at"])
    return jsonify({"notifications": notifications})


@app.route("/api/notifications/<int:student_id>/read", methods=["POST"])
def mark_read(student_id):
    """Tandai semua notifikasi mahasiswa sebagai sudah dibaca."""
    db.mark_notifications_read(student_id)
    return jsonify({"message": "Notifikasi ditandai sudah dibaca"})


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Jalankan background thread untuk heartbeat, monitor, dan bootstrap election
    # Sama persis dengan pola di bagian __main__ pada payment_service.py demo
    election.start_background_threads()

    log(f"Quiz Service starting on port {election.PORT}")
    app.run(host="0.0.0.0", port=election.PORT, threaded=True)
