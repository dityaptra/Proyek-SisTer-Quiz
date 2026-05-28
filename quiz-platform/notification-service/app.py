# app.py — Notification Service
# Mengonsumsi pesan dari RabbitMQ dan menyimpan notifikasi ke MySQL.
# Diadopsi dan dimodifikasi dari messaging/worker.py pada demo dist-system.
#
# Perbedaan dengan worker.py di demo:
# - Queue diganti dari payment_requests ke quiz.submission.result
# - Hasil diproses dengan menyimpan notifikasi ke MySQL (bukan ke queue lain)
# - Tidak ada simulasi random failure karena ini notifikasi yang harus reliable

import os
import json
import time
import mysql.connector
from mysql.connector import pooling

# Konfigurasi RabbitMQ dan MySQL dari environment variable
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
NOTIF_QUEUE = os.getenv("NOTIF_QUEUE", "quiz.submission.result")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "mysql"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "quiz_platform"),
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def save_notification(student_id: int, message: str):
    """Simpan notifikasi ke tabel notifications di MySQL."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (student_id, message) VALUES (%s, %s)",
        (student_id, message)
    )
    conn.commit()
    cursor.close()
    conn.close()

def wait_for_rabbitmq(max_retries=10):
    """
    Tunggu RabbitMQ siap sebelum mulai consume.
    Pola retry ini diadopsi dari worker.py demo.
    """
    import pika
    for i in range(max_retries):
        try:
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBIT_HOST)
            )
            conn.close()
            print(f"[notification-service] RabbitMQ ready", flush=True)
            return True
        except Exception:
            print(f"[notification-service] Waiting for RabbitMQ... ({i+1}/{max_retries})", flush=True)
            time.sleep(3)
    return False

def main():
    import pika

    if not wait_for_rabbitmq():
        print("[notification-service] Could not connect to RabbitMQ, exiting", flush=True)
        return

    conn = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBIT_HOST, heartbeat=60)
    )
    ch = conn.channel()

    # Deklarasi queue yang sama dengan yang di-publish oleh Quiz Service
    # Pola ini sama dengan queue_declare di worker.py demo
    ch.queue_declare(queue=NOTIF_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)

    def on_message(ch, method, properties, body: bytes):
        """
        Callback saat pesan diterima dari RabbitMQ.
        Diadopsi dari on_message() di worker.py demo.
        """
        try:
            data = json.loads(body.decode("utf-8"))
            print(f"[notification-service] Received: {data}", flush=True)

            student_id  = int(data.get("student_id", 0))
            student_name = data.get("student_name", "Mahasiswa")
            quiz_title  = data.get("quiz_title", "Ujian")
            score       = data.get("score", 0)

            # Buat pesan notifikasi yang akan ditampilkan ke mahasiswa
            message = (
                f"Ujian '{quiz_title}' telah selesai dikoreksi. "
                f"Skor kamu: {score}/100. Selamat!"
                if score >= 60 else
                f"Ujian '{quiz_title}' telah selesai dikoreksi. "
                f"Skor kamu: {score}/100. Semangat belajar lagi!"
            )

            save_notification(student_id, message)
            print(f"[notification-service] Saved notification for student_id={student_id}", flush=True)

        except Exception as e:
            print(f"[notification-service] Error processing message: {e}", flush=True)
        finally:
            # Selalu acknowledge pesan agar tidak diproses ulang
            ch.basic_ack(delivery_tag=method.delivery_tag)

    ch.basic_consume(queue=NOTIF_QUEUE, on_message_callback=on_message, auto_ack=False)
    print(f"[notification-service] Waiting for messages on queue '{NOTIF_QUEUE}'...", flush=True)
    ch.start_consuming()

if __name__ == "__main__":
    # Tunggu MySQL siap dulu sebelum start
    time.sleep(5)
    main()
