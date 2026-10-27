# Skenario Pengajaran dan Investigasi

## Narasi

Portal PMB menerima keluhan bahwa beberapa pendaftaran berhenti pada status `PROCESSING`. Tim operasi menemukan seluruh container masih hidup sehingga pemeriksaan status proses saja tidak cukup untuk menentukan penyebab.

Mahasiswa bertindak sebagai tim operasi dan keamanan. Mereka harus membuktikan apakah autentikasi, API, database transaksi, atau worker menjadi sumber gangguan. Penilaian harus menggunakan event yang tersimpan pada centralized logging, bukan asumsi berdasarkan status container.

## Tahap praktikum

### Tahap A — Baseline

1. Jalankan mode `none`.
2. Kirim pendaftaran normal.
3. Catat request ID dan rentang waktu.
4. Buktikan status akhir `VERIFIED`.
5. Susun baseline urutan event dan waktu penyelesaian.

### Tahap B — Failure injection

1. Aktifkan mode `timeout`.
2. Kirim pendaftaran baru.
3. Jangan langsung membaca kode aplikasi.
4. Gunakan database transaksi dan centralized log untuk menemukan service pertama yang menghasilkan `WARN` atau `ERROR`.
5. Rekonstruksi urutan `verification_started`, `verification_retry`, dan `dependency_timeout`.
6. Buktikan dampaknya pada status transaksi.

### Tahap C — Recovery

1. Kembalikan mode menjadi `none`.
2. Kirim transaksi baru.
3. Pastikan transaksi baru menjadi `VERIFIED`.
4. Jelaskan mengapa transaksi lama yang `FAILED` tidak otomatis berubah.
5. Usulkan strategi retry terkontrol atau dead-letter queue.

### Tahap D — Resilience logging

1. Hentikan `log-db` sementara.
2. Hasilkan transaksi baru.
3. Amati retry dan penggunaan buffer Fluent Bit.
4. Jalankan kembali `log-db`.
5. Buktikan backlog terkirim.
6. Jelaskan mengapa hasil ini belum membuktikan exactly-once delivery.

## Pertanyaan analitis

1. Mengapa status container `Up` tidak membuktikan fungsi bisnis sehat?
2. Apa perbedaan event time, waktu penerimaan collector, dan waktu penyimpanan database?
3. Mengapa nama dan email tidak dimasukkan ke structured log?
4. Apa risiko penggunaan `request_id` dari client tanpa validasi?
5. Apa yang terjadi bila buffer Fluent Bit mencapai batas 256 MB?
6. Bagaimana mendeteksi duplikasi record setelah retry?
7. Kapan PostgreSQL tidak lagi sesuai sebagai backend log utama?
8. Kontrol apa yang harus ditambahkan sebelum arsitektur serupa dipakai pada produksi?

## Evidence minimum

- screenshot atau keluaran status service;
- request ID baseline dan insiden;
- query kronologi untuk kedua request ID;
- jumlah retry dan kode kegagalan;
- bukti recovery transaksi baru;
- hasil pemeriksaan secret;
- checksum konfigurasi;
- pernyataan keterbatasan pengujian.
