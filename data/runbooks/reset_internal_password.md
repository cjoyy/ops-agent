# Runbook: Reset Password Akun Internal

Gunakan runbook ini untuk permintaan reset password akun internal karyawan atau contractor. Jangan lakukan reset sebelum identitas requester diverifikasi melalui kanal resmi seperti SSO recovery, manager approval, atau tiket dari email perusahaan.

Cari akun di admin console IAM dengan username atau email perusahaan. Pastikan status akun aktif dan tidak sedang ditandai compromised. Jika akun ditandai risky, hentikan proses reset biasa dan ikuti prosedur security review.

Reset password menggunakan tombol `Force password reset` di IAM console atau perintah `iamctl users reset-password --user <email> --force-change`. Jangan mengirim password sementara lewat chat publik; gunakan kanal aman yang disetujui perusahaan.

Setelah reset, minta user login ulang dan mengaktifkan MFA jika belum aktif. Catat waktu reset, approver, dan metode verifikasi identitas di tiket untuk audit.
