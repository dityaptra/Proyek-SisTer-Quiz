# Quiz Platform — Distributed System UAS

Proyek ini merupakan **ekstensi dari demo `payment-system/`** pada repository [dist-system](https://github.com/goshlive/dist-system), dengan perubahan domain dari payment menjadi quiz/assessment platform untuk ujian mahasiswa.

## Perubahan dari Demo

| Komponen Demo | Ekstensi Proyek Ini |
|---|---|
| `payment_service.py` — Bully Algorithm | `ring_election.py` — Ring-based Algorithm |
| `payment_service.py` — In-memory dict | `db.py` — MySQL persistent storage |
| `order_service.py` — Domain payment | `app.py` — Domain quiz/assessment |
| `messaging/worker.py` — Queue terpisah | `notification-service/` — Terintegrasi ke system |
| Tidak ada GUI | Vue.js frontend |
| Tidak ada load balancer | Nginx round-robin |

## Arsitektur

```
Vue Frontend
     │ HTTP
  Nginx (load balancer, round-robin)
     │
  ┌──┴──────────────┐
quiz-1  quiz-2  quiz-3   ← Ring-based Leader Election
  └──────┬──────────┘
         │ MySQL
         │ RabbitMQ publish
         │
  Notification Service   ← RabbitMQ consume → MySQL
```

## Cara Menjalankan

### Prasyarat
- Docker Desktop sudah berjalan
- Node.js 20+ (untuk build Vue)

### Langkah 1: Build Vue Frontend

```bash
cd quiz-platform/frontend
npm install
npm run build
cd ..
```

### Langkah 2: Jalankan Semua Service

```bash
cd quiz-platform
docker compose up -d --build
```

### Langkah 3: Tunggu Semua Service Siap

```bash
docker compose logs -f
```

Tunggu hingga muncul log seperti:
```
quiz-node-1  | [quiz-1 id=1] Bootstrap: starting initial election
quiz-node-1  | [quiz-1 id=1] BECOME LEADER -> broadcast coordinator to all nodes
```

### Langkah 4: Akses Aplikasi

| URL | Keterangan |
|---|---|
| http://localhost | Aplikasi utama (Vue frontend) |
| http://localhost:15672 | RabbitMQ Management UI (guest/guest) |
| http://localhost:5001/status | Status node quiz-1 |
| http://localhost:5002/status | Status node quiz-2 |
| http://localhost:5003/status | Status node quiz-3 |

### Login

Gunakan NIM berikut untuk login:
- `2021001` — Andi Pratama
- `2021002` — Budi Santoso
- `2021003` — Citra Dewi
- `2021004` — Dian Rahayu
- `2021005` — Eko Firmansyah

## Menguji Leader Election

### Cek siapa leader saat ini:
```bash
curl http://localhost:5001/status
curl http://localhost:5002/status
curl http://localhost:5003/status
```

### Simulasi leader mati:
```bash
# Misalnya quiz-3 adalah leader, matikan dia
docker compose stop quiz-3

# Tunggu beberapa detik, lalu cek leader baru
curl http://localhost:5001/status
```

### Hidupkan kembali:
```bash
docker compose start quiz-3
```

## Menghentikan Semua Service

```bash
docker compose down
# Untuk menghapus data MySQL juga:
docker compose down -v
```

## Struktur File

```
quiz-platform/
├── quiz-service/
│   ├── app.py             # Flask REST API + RPC handler
│   ├── ring_election.py   # Ring-based Leader Election
│   ├── db.py              # MySQL queries
│   ├── requirements.txt
│   └── Dockerfile
├── notification-service/
│   ├── app.py             # RabbitMQ consumer
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/         # Login, Dashboard, QuizRoom, Result, Notifications
│   │   ├── router/
│   │   └── App.vue
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── nginx.conf         # Load balancer config
├── db/
│   └── init.sql           # Schema + seed data
└── docker-compose.yml
```
