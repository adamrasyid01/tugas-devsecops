# LAPORAN PRAKTIKUM

## TUGAS BAB 6 — Skenario Logging dari Aplikasi PMB

**Dosen Pengampu:** Ferry Astika Saputra, S.T., M.Sc.

**Disusun oleh:**

- Adam Rasyid Nurmuhammad
- 3126640025
- D4-IT-B

**Program Studi Sarjana Terapan**  
**Jurusan Teknik Informatika**  
**Departemen Teknik Informatika dan Komputer**  
**Politeknik Elektronika Negeri Surabaya**  
**2026**

## 0. Persiapan

Jalankan persiapan dan validasi proyek:

```bash
bash scripts/setup.sh
./scripts/validate.sh
docker compose up -d --build
```

![Persiapan proyek](<pmb-lab-img/0.Persiapan.png>)

Pada awalnya, `pmb-lab-log-db-1` berstatus *unhealthy*.

![Log DB unhealthy](<pmb-lab-img/0.1docker gagal karena db unhealthy.png>)

Log menunjukkan bahwa container `log-db` tidak memiliki izin membaca folder `init-log` yang dipasang ke `/docker-entrypoint-initdb.d`. Image PostgreSQL memeriksa dan menjalankan skrip di folder tersebut saat inisialisasi.

![Kesalahan izin folder init-log](<pmb-lab-img/0.4 izin membaca folder init-log yang dipasang ke docker-entrypoint-initdb.d.png>)

Perbaiki izin folder dan skrip, kemudian jalankan kembali Compose:

```bash
sudo chmod 755 init-log init-app
sudo chmod 755 init-log/*.sh init-app/*.sh
docker compose up -d
docker compose ps
```

Awalnya `app-db` sudah *healthy*, tetapi `log-db` masih *restarting*. Periksa pesan terbarunya:

```bash
docker compose logs --tail 80 log-db
```

![Pemeriksaan log database](<pmb-lab-img/0.5 docker logs berhasil muncul db nya.png>)

Setelah database berhasil dimuat, startup masih terhenti pada `auth-service`.

![Kesalahan saat menjalankan auth-service](<pmb-lab-img/0.6 jalankan dengan docker compose up -d error di auth service.png>)

Periksa log layanan:

```bash
docker compose logs --tail 100 auth-service
```

![Permission denied pada auth-service](<pmb-lab-img/0.7 cek dengan docker compose logs --tail 100 auth-service permission denied.png>)

Beri izin baca pada kode aplikasi, lalu bangun ulang image:

```bash
chmod -R a+rX app
docker compose up -d --build
```

![Perbaikan izin folder aplikasi](<pmb-lab-img/0.8 Tambah permission untuk app.png>)

Seluruh service kemudian dapat berjalan, tetapi pemeriksaan portal dari VM masih gagal.

![Seluruh service berjalan](<pmb-lab-img/0.9Berhasil menjalankan seluruh service.png>)

![Koneksi ke port 8080 gagal](<pmb-lab-img/0.10 curl 127.0.0.1 8080 gagal.png>)

Aplikasi sehat di dalam container, tetapi port `8080` belum tersambung ke VM karena `registration-api` hanya terhubung ke jaringan Docker `internal`. Tambahkan jaringan `host-access` pada `fluent-bit` dan `registration-api` di `compose.yaml`, lalu definisikan jaringannya pada bagian bawah file.

![Jaringan pada registration-api](<pmb-lab-img/0.12 compose yaml regsitration-api networks.png>)

![Jaringan pada fluent-bit](<pmb-lab-img/0.11 compose yaml fluent-bit neworks.png>)

![Definisi jaringan host-access](<pmb-lab-img/0.13 paling bawah.png>)

Setelah konfigurasi valid, jalankan ulang layanan dan periksa hasilnya:

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:2020/api/v1/health
```

![Portal berhasil berjalan](<pmb-lab-img/0.14 Berhasil.png>)

![Pemeriksaan Fluent Bit](<pmb-lab-img/0.15 curl api health dan docker compose ps fluent-bit.png>)

Pemeriksaan awal `verify.sh` menunjukkan seluruh layanan siap dan log telah tersimpan. Pada saat itu belum ada transaksi pendaftaran, sehingga pemeriksaan transaksi baru dapat lulus setelah Tahap A dijalankan.

![Pemeriksaan awal verify.sh](<pmb-lab-img/0.16 verify sh berhasil.png>)

## 1. Tahap A — Normal (Baseline)

Jalankan mode normal dan buat pendaftaran:

```bash
./scripts/set-incident.sh none
./scripts/demo-normal.sh
./scripts/verify.sh
```

![Transaksi normal pada Tahap A](<pmb-lab-img/1.1 Tahap A - Baseline.png>)

Transaksi dengan `request_id` `REQ-b327d759254442a39b01a73a602b4033` mencapai status `VERIFIED` dalam satu percobaan. Pemeriksaan `verify.sh` kemudian lulus.

![Verifikasi Tahap A](<pmb-lab-img/1.2 Tahap A - cek dengan verify sh.png>)

## 2. Tahap B — Failure Injection

Jalankan simulasi insiden:

```bash
./scripts/demo-incident.sh
```

![Hasil simulasi insiden](<pmb-lab-img/2.1 Tahap B Failure injection demo-incident sh.png>)

Pada transaksi dengan `request_id` `REQ-90d7301bad1c4cc9a26867730132913c`, pendaftaran dikirim pada 13:45:13 dan mulai diproses oleh `verification-worker`. Service tersebut menghasilkan peringatan pertama melalui event `verification_retry` pada percobaan 1, lalu mengulang sampai percobaan 3. Pada 13:45:16 muncul `dependency_timeout` dengan tingkat `ERROR` dan kode `VERIFY-TIMEOUT`. Akibatnya, transaksi berstatus `FAILED` dengan `attempt = 3`. Pemeriksaan log tidak menemukan indikasi kebocoran *secret* (`0` temuan).

![Kronologi event Tahap B](<pmb-lab-img/2.3 cuplikan 2 tabel event.png>)

![Status transaksi dan ringkasan log Tahap B](<pmb-lab-img/2.2 cuplikan 1 tabel INFO.png>)

## 3. Tahap C — Recovery

Kembalikan mode insiden ke `none` dan buat transaksi baru:

```bash
./scripts/set-incident.sh none
./scripts/demo-normal.sh
```

![Transaksi pemulihan pada Tahap C](<pmb-lab-img/3.1 Tahap C — Recovery scriptnya.png>)

Transaksi baru dengan `request_id` `REQ-f7b76e87e6004a5ca48dcc206d85873a` mencapai status `VERIFIED` dalam satu percobaan. Transaksi Tahap B yang sudah `FAILED` tidak otomatis diproses ulang; pemulihan dibuktikan melalui transaksi baru.

![Status transaksi insiden lama tetap FAILED](<pmb-lab-img/3.2 pastikan transaksi insiden lama masih FAILED.png>)

## 4. Tahap D — Resilience Logging

Hentikan `log-db`, buat transaksi normal, amati retry Fluent Bit, lalu jalankan kembali database log:

```bash
docker compose stop log-db
./scripts/demo-normal.sh
docker compose logs --tail 100 fluent-bit
docker compose start log-db
```

![Transaksi saat log-db berhenti](<pmb-lab-img/4.1 Tahap D — Resilience logging hentikan db.png>)

Saat `log-db` berhenti, transaksi `REQ-a7e4de96601841eaa45f3ee17b49d5bd` tetap berstatus `VERIFIED` dalam satu percobaan. Fluent Bit gagal mengirim log ke PostgreSQL dan menampilkan pesan `failed to flush chunk` beserta jadwal retry.

![Retry Fluent Bit saat log-db berhenti](<pmb-lab-img/4.2 Tahap D — Resilience logging Amati retry dan penggunaan buffer Fluent Bit..png>)

Setelah `log-db` kembali sehat, empat event untuk transaksi tersebut ditemukan di `logs.fluentbit`, sehingga backlog terbukti terkirim. Pengujian ini belum membuktikan *exactly-once delivery*.

## Pertanyaan Analitis

1. **Mengapa status container `Up` tidak membuktikan fungsi bisnis sehat?**  
   `Up` hanya menunjukkan proses container berjalan. Pada Tahap B, layanan tetap berjalan, tetapi verifikasi gagal setelah tiga percobaan dan transaksi berakhir `FAILED / VERIFY-TIMEOUT`. Fungsi bisnis perlu diperiksa melalui status transaksi dan kronologi event.

2. **Apa perbedaan tiga waktu pada log?**  
   *Event time* adalah saat aplikasi membuat event, yang tercantum pada `timestamp` di structured log. Waktu penerimaan collector adalah saat Fluent Bit menerima event, sedangkan waktu penyimpanan database adalah saat PostgreSQL berhasil menyimpannya. Ketiganya dapat berbeda saat terjadi antrean dan retry; skema lab belum menyimpan ketiganya sebagai kolom terpisah.

3. **Mengapa nama dan email tidak dimasukkan ke structured log?**  
   Nama dan email adalah data pribadi yang tidak diperlukan untuk menelusuri insiden. Proyek memakai `request_id`, `registration_id`, nama event, dan status agar transaksi tetap dapat ditelusuri tanpa menyalin data pribadi ke database log.

4. **Apa risiko `request_id` dari client tanpa validasi?**  
   Client dapat mengirim nilai yang terlalu panjang atau berisi karakter tak terduga, sehingga pencarian dan korelasi log menjadi tidak andal. Proyek memvalidasi formatnya dan membuat ID baru bila nilai yang diterima tidak valid.

5. **Apa yang terjadi bila buffer Fluent Bit mencapai 256 MB?**  
   Batas `storage.total_limit_size 256M` membatasi backlog untuk output PostgreSQL. Jika gangguan berlanjut dan batas tercapai, event lama dapat hilang sehingga kronologi log tidak lengkap.

6. **Bagaimana mendeteksi duplikasi record setelah retry?**  
   Cari event dengan kombinasi `request_id`, nama event, service, percobaan (`attempt`), dan isi yang sama, lalu hitung kemunculannya di `logs.fluentbit`.

7. **Kapan PostgreSQL tidak lagi sesuai sebagai backend log utama?**  
   Ketika volume masuk, masa retensi, atau kebutuhan pencarian membuat penyimpanan dan query log mengganggu kinerja serta kapasitas PostgreSQL. Pada kondisi itu perlu mengevaluasi backend log khusus; proyek ini memakai PostgreSQL untuk pembelajaran query dan investigasi, bukan sebagai ukuran kesiapan skala produksi.

8. **Kontrol apa yang perlu ditambahkan sebelum produksi?**  
   Gunakan HTTPS/TLS dan *secure cookie*, pengelolaan serta rotasi *secret*, pembatasan akses ke log, kebijakan retensi dan backup, pemantauan kapasitas buffer serta kegagalan pengiriman, dan mekanisme penanganan duplikasi.
