\pset pager off
\timing on

-- 1. Memastikan log dari ketiga service tersedia.
SELECT tag, count(*) AS total_event
FROM logs.fluentbit
GROUP BY tag
ORDER BY total_event DESC, tag;

-- 2. Kronologi event aplikasi. Cast aman dibatasi pada record JSON buatan aplikasi.
WITH events AS (
    SELECT time, tag, (data ->> 'log')::jsonb AS event
    FROM logs.fluentbit
    WHERE tag LIKE 'pmb.%'
      AND left(ltrim(data ->> 'log'), 1) = '{'
)
SELECT
    time,
    event ->> 'service' AS service,
    event ->> 'severity' AS severity,
    event ->> 'event' AS event_name,
    event ->> 'request_id' AS request_id,
    event ->> 'registration_id' AS registration_id,
    event ->> 'error_code' AS error_code
FROM events
ORDER BY time DESC
LIMIT 50;

-- 3. Semua event WARN dan ERROR per service.
WITH events AS (
    SELECT time, (data ->> 'log')::jsonb AS event
    FROM logs.fluentbit
    WHERE tag LIKE 'pmb.%'
      AND left(ltrim(data ->> 'log'), 1) = '{'
)
SELECT
    event ->> 'service' AS service,
    event ->> 'severity' AS severity,
    count(*) AS total
FROM events
WHERE event ->> 'severity' IN ('WARN', 'ERROR')
GROUP BY service, severity
ORDER BY total DESC, service;

-- 4. Ganti nilai request ID untuk merekonstruksi satu transaksi.
\set investigated_request_id 'REQ-GANTI-DENGAN-NILAI-AKTUAL'
WITH events AS (
    SELECT time, tag, (data ->> 'log')::jsonb AS event
    FROM logs.fluentbit
    WHERE tag LIKE 'pmb.%'
      AND left(ltrim(data ->> 'log'), 1) = '{'
)
SELECT
    time,
    event ->> 'service' AS service,
    event ->> 'event' AS event_name,
    event ->> 'severity' AS severity,
    event ->> 'attempt' AS attempt,
    event ->> 'error_code' AS error_code
FROM events
WHERE event ->> 'request_id' = :'investigated_request_id'
ORDER BY time;

-- 5. Laju ingest per menit.
SELECT date_trunc('minute', time) AS minute_bucket, count(*) AS total
FROM logs.fluentbit
GROUP BY minute_bucket
ORDER BY minute_bucket DESC
LIMIT 15;

-- 6. Pemeriksaan indikasi secret pada payload log.
SELECT time, tag, left(data ->> 'log', 300) AS suspicious_message
FROM logs.fluentbit
WHERE data ->> 'log' ~* '(password|passwd|authorization|bearer|cookie|session[_-]?secret|api[_-]?key)'
ORDER BY time DESC;

-- 7. Preview data sebelum retensi. Jangan hapus tanpa review.
SELECT count(*) AS candidate_for_deletion
FROM logs.fluentbit
WHERE time < CURRENT_TIMESTAMP - INTERVAL '7 days';

-- DELETE FROM logs.fluentbit
-- WHERE time < CURRENT_TIMESTAMP - INTERVAL '7 days';
