# Runbook: Cek Log Server untuk Debug Crash

Gunakan runbook ini saat service crash, restart loop, atau proses tiba-tiba berhenti. Tujuannya adalah mengumpulkan bukti sebelum state berubah karena restart otomatis atau deployment baru.

Untuk service systemd, gunakan `journalctl -u <service_name> --since "30 minutes ago" --no-pager`. Untuk container, gunakan `docker logs --since 30m <container_name>`. Simpan bagian log yang mengandung stack trace, panic, segmentation fault, out-of-memory, atau database connection error.

Periksa resource host dengan `free -m`, `df -h`, dan `top -b -n 1 | head -20`. Jika ada indikasi OOM, cari log kernel dengan `dmesg -T | grep -i "killed process"` untuk memastikan apakah kernel membunuh proses.

Lampirkan log, metric resource, versi deployment, dan waktu crash ke tiket. Jika crash terjadi setelah deployment terakhir, bandingkan commit atau image tag terbaru dan pertimbangkan rollback sesuai runbook deployment rollback.
