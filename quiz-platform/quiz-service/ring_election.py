# ring_election.py
# Implementasi Ring-based Leader Election sebagai pengganti Bully Algorithm
# yang digunakan pada demo payment-system dari repository dist-system.
#
# Perbedaan utama dengan Bully Algorithm di demo:
# - Bully: broadcast ke semua node dengan ID lebih tinggi (O(n^2) pesan)
# - Ring : pesan hanya melewati tetangga kanan satu per satu (O(n) pesan)
#
# Cara kerja:
# 1. Node yang mendeteksi leader mati mengirim ELECTION {candidate_id} ke tetangga kanan
# 2. Setiap node membandingkan ID kandidat dengan ID-nya sendiri,
#    meneruskan yang lebih besar ke tetangga kanan
# 3. Ketika pesan kembali ke pengirim awal (candidate_id == NODE_ID),
#    node itu mendeklarasikan diri sebagai leader
# 4. Leader broadcast COORDINATOR ke semua node

import os
import time
import threading
import logging
import requests
from typing import Optional, Dict

log_werkzeug = logging.getLogger("werkzeug")
log_werkzeug.setLevel(logging.ERROR)

# ─────────────────────────────────────────────
# Konfigurasi Node
# Dibaca dari environment variable yang di-set oleh docker-compose.yml,
# sama persis dengan pola yang digunakan di payment_service.py pada demo
# ─────────────────────────────────────────────
NODE_NAME = os.getenv("NODE_NAME", "quiz-1")
NODE_ID   = int(os.getenv("NODE_ID", "1"))
ALL_NODES_RAW = os.getenv("ALL_NODES", "quiz-1:1,quiz-2:2,quiz-3:3")
PORT      = int(os.getenv("PORT", "5000"))

# Bangun dictionary NODES: {node_id -> hostname}
# Contoh: {1: "quiz-1", 2: "quiz-2", 3: "quiz-3"}
NODES: Dict[int, str] = {}
for item in [x.strip() for x in ALL_NODES_RAW.split(",") if x.strip()]:
    host, sid = item.rsplit(":", 1)
    NODES[int(sid)] = host

SELF_URL = f"http://{NODE_NAME}:{PORT}"

# Urutkan node_id untuk menentukan posisi ring
SORTED_IDS = sorted(NODES.keys())

def get_next_node_id() -> Optional[int]:
    """
    Dapatkan ID tetangga kanan dalam ring.
    Node terakhir dalam ring terhubung kembali ke node pertama (circular).
    Contoh ring: 1 -> 2 -> 3 -> 1 -> ...
    """
    try:
        idx = SORTED_IDS.index(NODE_ID)
        next_idx = (idx + 1) % len(SORTED_IDS)
        return SORTED_IDS[next_idx]
    except ValueError:
        return None

def get_next_node_url() -> Optional[str]:
    """Dapatkan URL lengkap tetangga kanan dalam ring."""
    next_id = get_next_node_id()
    if next_id is None:
        return None
    return f"http://{NODES[next_id]}:{PORT}"

# ─────────────────────────────────────────────
# State Global (thread-safe dengan lock)
# Mengadopsi pola yang sama dari payment_service.py di demo
# ─────────────────────────────────────────────
state_lock         = threading.Lock()
leader_id:         Optional[int] = None
leader_url:        Optional[str] = None
is_leader:         bool = False
election_in_progress: bool = False
last_heartbeat:    float = time.time()

def log(msg: str):
    """Format log dengan nama node, sama seperti di demo."""
    print(f"[{NODE_NAME} id={NODE_ID}] {msg}", flush=True)


# ─────────────────────────────────────────────
# Fungsi Komunikasi Antar Node
# ─────────────────────────────────────────────

def send_to_next(endpoint: str, payload: dict, timeout: float = 1.0) -> bool:
    """
    Kirim HTTP POST ke tetangga kanan dalam ring.
    Mengembalikan True jika berhasil, False jika gagal (node down).
    """
    url = get_next_node_url()
    if not url:
        return False
    try:
        requests.post(f"{url}{endpoint}", json=payload, timeout=timeout)
        return True
    except Exception:
        return False

def broadcast_to_all(endpoint: str, payload: dict):
    """
    Kirim pesan ke semua node lain (digunakan saat mengumumkan leader baru).
    Best-effort: node yang tidak responsif diabaikan.
    Mengadopsi pola broadcast() dari payment_service.py di demo.
    """
    for nid, host in NODES.items():
        if nid == NODE_ID:
            continue
        try:
            requests.post(
                f"http://{host}:{PORT}{endpoint}",
                json=payload,
                timeout=0.8
            )
        except Exception:
            pass


# ─────────────────────────────────────────────
# Logika Ring Election
# ─────────────────────────────────────────────

def become_leader():
    """
    Deklarasikan node ini sebagai leader baru.
    Broadcast COORDINATOR ke semua node agar semua memperbarui state mereka.
    """
    global leader_id, leader_url, is_leader, election_in_progress, last_heartbeat
    with state_lock:
        leader_id    = NODE_ID
        leader_url   = SELF_URL
        is_leader    = True
        election_in_progress = False
        last_heartbeat = time.time()

    log(f"BECOME LEADER -> broadcast coordinator to all nodes")
    broadcast_to_all("/coordinator", {
        "leader_id":  NODE_ID,
        "leader_url": SELF_URL
    })

def start_election():
    """
    Mulai proses Ring Election.
    Node ini mengirim pesan ELECTION dengan candidate_id = NODE_ID ke tetangga kanan.
    Mencegah election ganda dengan flag election_in_progress.
    """
    global election_in_progress
    with state_lock:
        if election_in_progress:
            return
        election_in_progress = True

    log(f"ELECTION started (ring-based) -> sending to next node")
    send_to_next("/election", {"candidate_id": NODE_ID, "initiator_id": NODE_ID})

def handle_election_message(candidate_id: int, initiator_id: int):
    """
    Proses pesan ELECTION yang diterima dari tetangga kiri.
    Inilah inti dari Ring Election Algorithm:
    - Jika candidate_id == NODE_ID: pesan sudah keliling penuh, kita yang menang
    - Jika candidate_id > NODE_ID: teruskan apa adanya (kandidat lebih kuat)
    - Jika candidate_id < NODE_ID: ganti dengan NODE_ID lalu teruskan
    """
    global election_in_progress

    with state_lock:
        election_in_progress = True

    if candidate_id == NODE_ID:
        # Pesan sudah satu putaran penuh dan kembali ke pengirim awal.
        # Artinya NODE_ID ini adalah yang terbesar di seluruh ring.
        log(f"ELECTION message returned to initiator -> I am the new leader")
        become_leader()

    elif candidate_id > NODE_ID:
        # Kandidat lebih kuat, teruskan pesan tanpa perubahan
        log(f"ELECTION forward candidate_id={candidate_id} (higher than mine={NODE_ID})")
        send_to_next("/election", {
            "candidate_id": candidate_id,
            "initiator_id": initiator_id
        })

    else:
        # NODE_ID lebih besar, ganti candidate_id dengan NODE_ID lalu teruskan
        log(f"ELECTION replace candidate_id={candidate_id} with mine={NODE_ID}")
        send_to_next("/election", {
            "candidate_id": NODE_ID,
            "initiator_id": initiator_id
        })

def handle_coordinator_message(new_leader_id: int, new_leader_url: str):
    """
    Terima pengumuman leader baru dari node yang memenangkan election.
    Perbarui state lokal semua node.
    """
    global leader_id, leader_url, is_leader, election_in_progress, last_heartbeat
    with state_lock:
        leader_id    = new_leader_id
        leader_url   = new_leader_url
        is_leader    = (NODE_ID == new_leader_id)
        election_in_progress = False
        last_heartbeat = time.time()

    log(f"COORDINATOR received: leader is now node-{new_leader_id}")


# ─────────────────────────────────────────────
# Background Threads
# Mengadopsi pola heartbeat_loop dan monitor_loop dari payment_service.py demo
# ─────────────────────────────────────────────

def heartbeat_loop():
    """
    Leader mengirim heartbeat ke semua node setiap 2 detik.
    Node lain menggunakan heartbeat ini untuk memastikan leader masih hidup.
    Sama persis polanya dengan heartbeat_loop() di payment_service.py demo.
    """
    while True:
        time.sleep(2.0)
        with state_lock:
            if not is_leader:
                continue
            hb_payload = {"leader_id": leader_id, "leader_url": leader_url}

        for nid, host in NODES.items():
            if nid == NODE_ID:
                continue
            try:
                requests.post(
                    f"http://{host}:{PORT}/heartbeat",
                    json=hb_payload,
                    timeout=1.0
                )
            except Exception:
                pass

def monitor_loop():
    """
    Setiap node non-leader memantau apakah heartbeat masih datang dari leader.
    Jika tidak ada heartbeat selama lebih dari 8 detik, anggap leader mati
    dan mulai election baru.
    Sama polanya dengan monitor_loop() di payment_service.py demo.
    """
    while True:
        time.sleep(1.0)
        with state_lock:
            if is_leader:
                continue
            lh = last_heartbeat
            in_election = election_in_progress

        if not in_election and (time.time() - lh) > 8.0:
            log("Leader timeout detected -> starting new election")
            start_election()

def bootstrap():
    """
    Jalankan election pertama kali saat service baru hidup.
    Delay berbeda per node untuk menghindari collision saat semua node
    startup bersamaan, sama seperti pola bootstrap di demo.
    """
    time.sleep(2.0 + 0.5 * NODE_ID)
    log("Bootstrap: starting initial election")
    start_election()

def start_background_threads():
    """Jalankan semua background thread. Dipanggil dari app.py saat startup."""
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=monitor_loop,   daemon=True).start()
    threading.Thread(target=bootstrap,      daemon=True).start()
    log(f"Ring election initialized. Ring order: {SORTED_IDS}")
    log(f"My right neighbor: node-{get_next_node_id()}")
