[中文](README.md) | [English](README_en.md) | [Bahasa Indonesia](README_id.md)
<div align="center">

GKI BakaSU SUSFS

Membangun kernel Android GKI melalui GitHub Actions dengan integrasi BakaSU dan SUSFS.

![Release](https://img.shields.io/github/v/release/coolzyd9107/GKIBakaSUSUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f) ![Build Kernel](https://github.com/zhuzhuzihan/GKIBakaSUSUSFS/actions/workflows/main.yml/badge.svg) ![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc) ![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square) ![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)

</div>

简体中文 | English | Bahasa Indonesia

Tentang Proyek

Repositori ini menyediakan alur kerja build berbasis cloud melalui GitHub Actions untuk membangun kernel Android GKI dan mengemasnya menjadi ZIP instalasi AnyKernel3 berdasarkan Android GKI KMI dan tingkat patch keamanan.

Build standar mengintegrasikan BakaSU. Fitur tambahan dapat diaktifkan melalui konfigurasi workflow. Anda juga dapat memilih Clean build untuk membangun kernel tanpa integrasi KernelSU, SUSFS, maupun patch fitur opsional.

Versi kernel dan revisi rilis diambil dari matriks JSON di dalam direktori data/android*/. Data tersebut diperbarui secara berkala melalui workflow sinkronisasi data.

Pemberitahuan Penting

Setelah dilakukan perombakan besar pada proyek, jumlah tahapan build dan artefak yang dihasilkan meningkat secara signifikan. Akibatnya, proses build dan rilis untuk seluruh versi kernel membutuhkan waktu yang sangat lama.

Oleh karena itu, kami tidak akan lagi menjalankan build dan menerbitkan rilis untuk semua versi kernel secara rutin, termasuk ketika BakaSU mendapatkan pembaruan besar. Kebijakan ini bertujuan mengurangi penggunaan sumber daya runner publik GitHub Actions dalam waktu lama serta mencegah penggunaan sumber daya komputasi secara berlebihan.

Pengguna disarankan melakukan fork terhadap repositori ini, kemudian membangun hanya versi kernel tertentu yang dibutuhkan melalui repositori fork masing-masing. Cara ini dapat mengurangi waktu build dan penggunaan sumber daya secara signifikan.

Kami mohon maaf atas ketidaknyamanan yang ditimbulkan. Untuk petunjuk penggunaan repositori utama maupun repositori hasil fork, silakan baca bagian terkait dalam README ini.

Target KMI yang Didukung
Android KMI	Seri Kernel	Opsi build_target
Android 12	5.10	android12-5.10
Android 13	5.10	android13-5.10
Android 13	5.15	android13-5.15
Android 14	5.15	android14-5.15
Android 14	6.1	android14-6.1
Android 15	6.6	android15-6.6
Android 16	6.12	android16-6.12
Android 17	6.18	android17-6.18

Seri kernel 5.10 dan 5.15 masing-masing digunakan oleh beberapa target Android KMI. Khusus kernel 5.15, Android 13 dan Android 14 menggunakan nomor seri kernel yang sama. Oleh karena itu, KMI tidak dapat ditentukan hanya berdasarkan nomor versi seperti 5.15.xxx. Saat membangun versi tertentu, Anda harus memilih versi Android yang sesuai secara manual.

Android 17 / 6.18 saat ini sudah mendukung build dasar. Beberapa komponen tambahan akan dilewati secara otomatis sesuai dengan status dukungan dari upstream.

Menjalankan Build
Buka halaman Actions pada repositori.
Pilih workflow Build Kernel, kemudian klik Run workflow.
Pilih target KMI pada build_target, atau pilih all untuk membangun seluruh target. Opsi ini hanya mendukung satu pilihan. Jika ingin membangun beberapa target tanpa membangun semuanya, jalankan workflow secara terpisah untuk setiap target.
Atur fitur opsional dan release_type sesuai kebutuhan.
Mulai workflow.
Setelah build selesai, unduh artefak melalui bagian Artifacts pada halaman detail proses build. Jika sebuah Release dibuat, paket juga dapat diunduh melalui halaman Releases.
Memfilter Berdasarkan Versi Kernel

Aktifkan build_kernel_version untuk memfilter build berdasarkan versi kernel. Filter versi ini memiliki prioritas lebih tinggi daripada opsi pemilihan versi biasa.

Parameter kernel_version_filter menerima nomor versi lengkap atau wildcard seri kernel.

Input	Fungsi
6.6.66	Membangun versi 6.6.66 berdasarkan data versi dari KMI yang dipilih
6.6.X atau 6.6.x	Membangun semua versi patch 6.6 yang tersedia dalam data KMI tersebut

Aturan pemilihan:

5.10: kernel_android_version harus diatur ke android12 atau android13.
5.15: kernel_android_version harus diatur ke android13 atau android14.
6.1, 6.6, 6.12, dan 6.18: Workflow otomatis menggunakan target KMI Android 14, 15, 16, dan 17 yang sesuai. Pemilihan versi Android secara manual tidak diperlukan.

Tingkat patch keamanan, revisi rilis, dan versi LTS diambil dari data JSON yang sesuai.

Build yang difilter ke versi kernel tertentu tidak akan membuat GitHub Release, meskipun release_type diatur ke pre-release atau release.

Jenis Rilis

Untuk build biasa, release_type menyediakan opsi berikut:

Actions: Hanya menyimpan artefak build di GitHub Actions tanpa membuat Release. Ini merupakan opsi default.
Pre-Release: Membuat rilis pratinjau setelah build berhasil di repositori utama.
Release: Membuat rilis resmi setelah build berhasil di repositori utama.

Repositori hasil fork hanya menghasilkan artefak Actions dan tidak akan menerbitkan Release ke repositori upstream.

Branch BakaSU

Jika kernelsu_branch dibiarkan kosong, workflow akan menggunakan branch main.

Anda juga dapat mengisi nama branch jarak jauh BakaSU atau SHA commit lengkap sepanjang 40 karakter. Pada awal proses build, workflow akan menentukan commit yang sesuai dengan branch tersebut dan mengunci revisinya untuk seluruh proses build.

Dengan demikian, semua target KMI dalam satu proses build akan menggunakan sumber kode BakaSU yang sama.

Catatan rilis akan menyertakan tautan ke commit BakaSU yang benar-benar digunakan dalam proses build.

Fitur Build Opsional
Opsi	Keterangan
clean_build	Membangun kernel tanpa BakaSU, SUSFS, maupun patch fitur opsional.
cancel_susfs	Menonaktifkan integrasi SUSFS. Secara default, SUSFS aktif. Android 17 / 6.18 akan melewati integrasi ini secara otomatis karena branch upstream belum tersedia.
use_zram	Mengaktifkan peningkatan ZRAM menggunakan LZ4KD. Otomatis dilewati pada Android 17 / 6.18 karena patch yang diperlukan belum tersedia.
use_bbg	Mengaktifkan patch anti-brick BBG.
use_rekernel	Mengaktifkan driver Re-Kernel. Fitur ini masih dalam tahap pengujian. Android 17 / 6.18 sementara melewatinya hingga repositori ini disesuaikan dengan struktur sumber kode upstream yang baru.
cve_2026_43499_patch	Menerapkan rangkaian perbaikan CVE-2026-43499. Aktif secara default. Otomatis dilewati pada kernel 6.18 karena patch yang telah disesuaikan belum tersedia di repositori ini.
build_bypass	Membangun Image tambahan dalam mode Bypass dan menyertakannya bersama Image biasa dalam paket instalasi.
droidspaces	Memilih patch kontainer Droidspaces: off, 678, 123, atau 345. Android 16 / 6.12 dan versi yang lebih baru menggunakan patch generik dari upstream.
droidspaces_ntsync	Mengaktifkan NTSync pada konfigurasi yang didukung. Droidspaces juga harus diaktifkan. Otomatis dilewati pada Android 17 / 6.18 karena patch yang diperlukan belum tersedia.

Mode Bypass ditujukan untuk membantu mendiagnosis masalah kompatibilitas versi modul kernel, bukan untuk melewati deteksi root. Jika diaktifkan, proses kompilasi penuh akan dijalankan sekali lagi sehingga waktu build menjadi lebih lama.

Saat melakukan instalasi, ikuti petunjuk pada skrip instalasi untuk memilih Image biasa atau Bypass Image.

Patch Droidspaces masih bersifat eksperimental. Perangkat dan versi kernel yang berbeda mungkin memerlukan percobaan pada slot patch yang berbeda.

Android 16 / 6.12 dan Android 17 / 6.18 hanya menyediakan satu slot patch. Anda cukup memilih nilai selain off untuk mengaktifkannya.

Upstream belum menyediakan patch kompatibilitas NTSync untuk Android 14 / 5.15. Mengaktifkan kombinasi ini akan menyebabkan build gagal, sehingga NTSync harus tetap dinonaktifkan untuk target tersebut.

Pada Android 17 / 6.18, NTSync akan dilewati secara otomatis jika patch yang diperlukan tidak tersedia.

Artefak Build

Nama artefak mencakup Android KMI, versi kernel lengkap, dan tingkat patch keamanan OS. Jika revisi upstream tersedia, revisi tersebut juga akan dicantumkan dalam nama file.

Contoh:

android14-5.15.148-2024-05-r25-BakaSU-AnyKernel3.zip


Jika mode Bypass diaktifkan, paket instalasi akan berisi Image dan Bypass-Image.

Pilih artefak yang sesuai dengan Android KMI dan branch kernel perangkat Anda. Sebelum melakukan flashing, cadangkan Image Boot bawaan dan pastikan tersedia metode pemulihan perangkat jika terjadi masalah.

Stock Config

Jika file config/stock_defconfig tersedia di repositori, proses build akan menggunakannya secara otomatis untuk melakukan penyamaran konfigurasi /proc/config.gz. Jika file tersebut tidak tersedia, langkah ini akan dilewati.

Anda dapat mengambil /proc/config.gz dari kernel bawaan perangkat, mengekstrak konfigurasi di dalamnya, lalu menyimpan hasilnya dengan nama:

config/stock_defconfig

Sinkronisasi Data GKI

Workflow Update GKI Version Data berjalan secara otomatis setiap hari Senin pukul 08.00 UTC. Workflow ini juga dapat dijalankan secara manual.

Prosesnya mencakup pengujian sinkronisasi, pembaruan data JSON, validasi matriks build, dan commit terhadap perubahan data yang dihasilkan.

Ucapan Terima Kasih
zzh20188: Penulis asli repositori build GKI upstream sebelumnya. Repositori ini tidak lagi menjadi bagian dari jaringan fork tersebut, dan zzh20188/GKI_KernelSU_SUSFS bukan lagi repositori upstream proyek ini.
coolzyd9107: Pemelihara repositori ini.
zhuzhuzihan: Perbaikan workflow serta pengembangan dan pemeliharaan Telegram Bot.
TanakaLun: Perbaikan workflow dan peningkatan fitur.
YC酱luyancib: Saran terkait Telegram Bot dan proses build.
AlexLiuDev233: Perbaikan masalah workflow.
cctv18: Peningkatan workflow, dukungan Android 6.12, dan saran perbaikan masalah SUSFS.

Untuk mendapatkan informasi build terbaru dan pemberitahuan perubahan penting, kunjungi kanal Telegram.

Untuk kanal resmi komunitas BakaSU, kunjungi BakaSU_Grp.
