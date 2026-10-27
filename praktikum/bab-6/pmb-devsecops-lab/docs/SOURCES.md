# Sumber Teknis

Rujukan berikut digunakan untuk keputusan desain dan validasi konfigurasi laboratorium. Versi dependency Python diverifikasi melalui metadata PyPI pada 27 Oktober 2026.

1. Docker. **Fluentd logging driver**. https://docs.docker.com/engine/logging/drivers/fluentd/
   - metadata `container_id`, `container_name`, `source`, dan `log`;
   - `fluentd-address`, `tag`, `fluentd-async`, dan batas buffer.

2. Fluent Bit. **PostgreSQL output plugin, Fluent Bit 4.2**. https://docs.fluentbit.io/manual/4.2/data-pipeline/outputs/postgresql
   - output `pgsql`;
   - struktur tabel `tag`, `time`, dan `data JSONB`;
   - parameter host, port, user, password, database, dan table.

3. Pallets. **Flask 3.1.3**. https://pypi.org/project/Flask/3.1.3/

4. Psycopg Team. **Psycopg 3.3.6**. https://pypi.org/project/psycopg/3.3.6/

5. Gunicorn Project. **Gunicorn 26.2.0**. https://pypi.org/project/gunicorn/26.2.0/

6. Python Software Foundation. **Requests 2.34.2**. https://pypi.org/project/requests/2.34.2/

7. PostgreSQL Global Development Group. **PostgreSQL 16 Documentation**. https://www.postgresql.org/docs/16/

## Batas interpretasi

Versi dependency yang dipin meningkatkan keterulangan build, tetapi tidak membuktikan bebas kerentanan. Sebelum penggunaan di luar laboratorium, jalankan Software Composition Analysis, periksa advisory terbaru, buat SBOM, dan tetapkan kebijakan pembaruan dependency.
