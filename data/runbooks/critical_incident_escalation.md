# Runbook: Eskalasi Insiden Critical

Gunakan runbook ini jika ada outage produksi, kebocoran data, kehilangan akses massal, payment failure luas, atau error yang berdampak ke pelanggan prioritas. Tujuan utama adalah koordinasi cepat, komunikasi jelas, dan mitigasi terukur.

Deklarasikan severity dengan format `SEV1` untuk outage total atau risiko data sensitif, dan `SEV2` untuk degradasi besar dengan workaround terbatas. Buat incident channel dengan nama `inc-YYYYMMDD-short-title` dan undang incident commander, owner service, on-call platform, dan customer support lead.

Incident commander harus membuat timeline, menunjuk lead mitigasi, dan mengirim update setiap 15 menit. Semua aksi produksi seperti rollback, restart cluster, atau perubahan konfigurasi harus dicatat dengan waktu, pelaku, dan hasil.

Setelah mitigasi stabil, lanjutkan postmortem dalam 2 hari kerja. Postmortem harus berisi impact, root cause, detection gap, corrective action, dan owner tiap action item.
