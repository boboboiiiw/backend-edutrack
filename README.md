# Edutrack Backend

## Overview

Edutrack adalah sebuah platform yang dirancang untuk memfasilitasi interaksi antara mahasiswa dan dosen, khususnya dalam hal berbagi materi dan informasi perkuliahan. Aplikasi ini memungkinkan mahasiswa untuk memposting konten edukatif, sementara dosen dapat memberikan rekomendasi pada postingan tersebut. Sistem ini juga mencakup fitur interaksi seperti komentar, suka, dan tidak suka, serta manajemen otentikasi pengguna berdasarkan peran (mahasiswa, dosen, tamu).

## Fitur Utama

* **Autentikasi Pengguna**: Sistem registrasi dan login untuk mahasiswa dan dosen. Pengguna dikategorikan sebagai "Mahasiswa" atau "Dosen" berdasarkan domain email (@student.itera.ac.id untuk Mahasiswa, @itera.ac.id untuk Dosen). Pengguna dengan domain email lain akan dianggap "Tamu" dan tidak diizinkan registrasi.
* **Profil Pengguna**: Pengguna dapat melihat dan memperbarui informasi profil mereka, termasuk nama dan program studi (khusus mahasiswa).
* **Manajemen Postingan**:
    * **Buat Postingan**: Mahasiswa dapat membuat postingan dengan judul, konten, dan referensi URL.
    * **Lihat Postingan**: Pengguna dapat melihat daftar postingan, dengan opsi filter untuk postingan sendiri.
    * **Detail Postingan**: Melihat detail postingan tunggal, termasuk referensi dan siapa yang merekomendasikan.
* **Interaksi Postingan**:
    * **Like/Dislike**: Pengguna dapat menyukai atau tidak menyukai postingan. Sistem melacak jumlah like dan dislike, serta mencegah duplikasi interaksi dari pengguna yang sama pada postingan yang sama.
    * **Komentar**: Pengguna dapat menambahkan komentar pada postingan.
* **Rekomendasi Dosen**: Dosen dapat merekomendasikan postingan, menandakan bahwa postingan tersebut memiliki kualitas baik atau relevan.

## Endpoint API

Berikut adalah daftar endpoint API yang tersedia:

### Autentikasi & Profil

* `POST /api/register`: Registrasi pengguna baru.
* `POST /api/login`: Login pengguna dan mendapatkan token JWT.
* `GET /api/me`: Mengambil profil pengguna yang sedang login.
* `PATCH /api/me`: Memperbarui profil pengguna yang sedang login.
* `POST /api/change-password`: Mengubah password pengguna.

### Postingan

* `POST /api/posts`: Membuat postingan baru (Hanya Mahasiswa).
* `GET /api/posts/all`: Mengambil daftar semua postingan (mendukung paginasi dan filter berdasarkan penulis).
* `GET /api/posts/{id}`: Mengambil detail postingan berdasarkan ID.
* `POST /api/posts/{id}/like`: Menyukai postingan.
* `POST /api/posts/{id}/dislike`: Tidak menyukai postingan.
* `POST /api/posts/{id}/recommend`: Dosen merekomendasikan postingan.
* `POST /api/posts/{id}/unrecommend`: Dosen membatalkan rekomendasi postingan.

### Komentar

* `POST /api/comments`: Menambah komentar baru pada postingan.
* `GET /api/comments/post/{post_id}`: Mengambil semua komentar untuk postingan tertentu (mendukung paginasi).

## Struktur Folder Backend (`backend_edutrack`)

```
backend_edutrack/
├── alembic/
│   └── versions/             # Skrip migrasi database.
├── backend_edutrack/
│   ├── models/               # Definisi model database (User, Post, Comment, URL, PostInteraction).
│   ├── scripts/              # Skrip utilitas, termasuk inisialisasi DB.
│   ├── tests/                # Unit tests untuk berbagai modul.
│   ├── utils/                # Modul utilitas (autentikasi, JWT).
│   ├── views/                # Handler API untuk autentikasi, postingan, dan komentar.
│   ├── __init__.py           # Konfigurasi aplikasi utama.
│   ├── routes.py             # Definisi rute API.
│   ├── security.py           # Logika keamanan aplikasi.
│   ├── development.ini       # Konfigurasi lingkungan pengembangan.
│   └── production.ini        # Konfigurasi lingkungan produksi.
├── alembic.ini               # Konfigurasi alat migrasi database.
├── requirements.txt          # Daftar dependensi proyek.
└── README.txt                # Dokumentasi proyek.
```

## Struktur Tabel Database (SQLAlchemy Models)

Berikut adalah tabel-tabel utama yang digunakan dalam database:

* **`users`**
    * `id` (Integer, Primary Key)
    * `name` (String)
    * `email` (String, Unique)
    * `password` (Text)
    * `role` (String) - 'Mahasiswa', 'Dosen', 'Tamu'
    * `prodi` (String, Nullable) - Program studi (khusus Mahasiswa)
    * `nim` (String, Unique, Nullable) - Nomor Induk Mahasiswa (khusus Mahasiswa)

* **`posts`**
    * `id` (Integer, Primary Key)
    * `title` (Text)
    * `content` (Text)
    * `created_at` (DateTime)
    * `author_id` (Integer, Foreign Key ke `users.id`)
    * `likes` (Integer, Default 0)
    * `dislikes` (Integer, Default 0)

* **`comments`**
    * `id` (Integer, Primary Key)
    * `content` (Text)
    * `created_at` (DateTime)
    * `post_id` (Integer, Foreign Key ke `posts.id`)
    * `user_id` (Integer, Foreign Key ke `users.id`)

* **`urls`**
    * `id` (Integer, Primary Key)
    * `url` (String, Unique)

* **`post_recommendations`** (Tabel asosiasi Many-to-Many)
    * `post_id` (Integer, Foreign Key ke `posts.id`, Primary Key)
    * `user_id` (Integer, Foreign Key ke `users.id`, Primary Key)

* **`post_references`** (Tabel asosiasi Many-to-Many)
    * `post_id` (Integer, Foreign Key ke `posts.id`)
    * `url_id` (Integer, Foreign Key ke `urls.id`)

* **`post_interactions`**
    * `id` (Integer, Primary Key)
    * `user_id` (Integer, Foreign Key ke `users.id`)
    * `post_id` (Integer, Foreign Key ke `posts.id`)
    * `interaction_type` (String) - 'like' atau 'dislike'
    * `created_at` (DateTime)
    * Unique constraint `_user_post_uc` pada `(user_id, post_id)` untuk memastikan satu interaksi per user per post.

## Cara Menjalankan Aplikasi

1.  **Ganti direktori ke proyek Anda**:
    ```bash
    cd backend_edutrack
    ```

2.  **Buat lingkungan virtual Python**:
    ```bash
    python3 -m venv env
    ```

3.  **Upgrade alat packaging**:
    ```bash
    env/bin/pip install --upgrade pip setuptools
    ```

4.  **Install proyek dengan semua dependensi, termasuk yang untuk testing**:
    ```bash
    env/bin/pip install -e ".[testing]"
    ```

5.  **Inisialisasi dan upgrade database menggunakan Alembic**:
    * Generate revisi pertama:
        ```bash
        env/bin/alembic -c development.ini revision --autogenerate -m "init"
        ```
    * Upgrade ke revisi tersebut:
        ```bash
        env/bin/alembic -c development.ini upgrade head
        ```

6.  **Load data default ke database (opsional)**:
    ```bash
    env/bin/initialize_backend_edutrack_db development.ini
    ```

7.  **Jalankan tes proyek (opsional)**:
    ```bash
    env/bin/pytest
    ```

8.  **Jalankan aplikasi**:
    ```bash
    env/bin/pserve development.ini
    ```

## Copyright

© 2025 Boy Sandro Sigiro. All rights reserved.
