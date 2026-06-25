# Runbook: Restart Service auth-api

Gunakan runbook ini khusus untuk service `auth-api` saat login gagal, token issuance lambat, atau health check auth API tidak stabil. Karena service ini berhubungan dengan autentikasi, selalu cek apakah ada incident security aktif sebelum restart.

Ambil log terakhir dengan `journalctl -u auth-api -n 300 --no-pager` dan cari error seperti `database timeout`, `redis unavailable`, atau `jwt signing key load failed`. Cek juga metric dependency auth-api, terutama Redis session store dan database identity.

Restart service dengan `sudo systemctl restart auth-api`, lalu tunggu 30 sampai 60 detik. Verifikasi status dengan `sudo systemctl is-active auth-api` dan health check dengan `curl -f http://localhost:8081/health/auth`.

Jika health check gagal setelah restart, jangan melakukan restart lebih dari dua kali. Eskalasikan ke owner identity platform dengan log, hasil health check, dan output `sudo systemctl status auth-api`.
