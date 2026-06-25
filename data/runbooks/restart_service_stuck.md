# Runbook: Restart Service yang Stuck

Gunakan runbook ini saat service tidak merespons, health check gagal, atau worker terlihat berhenti memproses request. Pastikan insiden dicatat di tiket sebelum melakukan restart, termasuk nama service, environment, waktu kejadian, dan gejala utama.

Langkah pertama adalah cek status service dengan `systemctl status <service_name>` atau `docker ps --filter name=<service_name>` sesuai runtime yang dipakai. Jika service masih hidup tapi stuck, ambil snapshot log terlebih dahulu dengan `journalctl -u <service_name> -n 200 --no-pager` atau `docker logs --tail 200 <container_name>` agar bukti error tidak hilang.

Restart service secara bertahap. Untuk host systemd, jalankan `sudo systemctl restart <service_name>` lalu verifikasi dengan `sudo systemctl status <service_name>`. Untuk container, gunakan `docker restart <container_name>` dan cek apakah container kembali healthy dalam 60 detik.

Setelah restart, validasi endpoint health check dengan `curl -f http://localhost:8080/health` atau endpoint health spesifik service. Jika service kembali stuck dalam 10 menit, jangan restart berulang tanpa investigasi; eskalasikan ke owner service dengan log terakhir, metric CPU/memory, dan timestamp restart.
