# Runbook: Troubleshoot Error 500 di API Gateway

Gunakan runbook ini ketika user menerima HTTP 500 dari API gateway. Error 500 biasanya berarti gateway gagal memproses request atau upstream service mengembalikan error yang tidak tertangani.

Mulai dengan cek request ID atau correlation ID dari response header. Cari jejaknya di log gateway menggunakan `grep "<request_id>" /var/log/api-gateway/gateway.log` atau query log terpusat dengan filter service `api-gateway` dan status `500`.

Periksa apakah error berasal dari gateway atau upstream. Jika log menunjukkan `upstream_status=500`, lanjutkan investigasi ke service tujuan. Jika log menunjukkan timeout, DNS failure, atau connection refused, cek konfigurasi route, service discovery, dan readiness upstream.

Validasi konfigurasi gateway sebelum reload. Jalankan `gatewayctl validate /etc/api-gateway/routes.yaml`, lalu reload dengan `sudo systemctl reload api-gateway` hanya jika konfigurasi valid. Jika error berdampak luas pada lebih dari satu route critical, buat incident bridge dan eskalasikan sebagai critical incident.
