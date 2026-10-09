[中文](README.md) | [English](README.en.md) | [Bahasa Indonesia](README.id.md)

<div align="center">

# GKI BakaSU SUSFS

Membangun kernel Android GKI berbasis GitHub Actions, mengintegrasikan BakaSU dan SUSFS.

[![Release](https://img.shields.io/github/v/release/coolzyd9107/GKI_BakaSU_SUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/releases)
[![Build Kernel](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml/badge.svg)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml)
[![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc)](https://t.me/BakaSUKernelBuilds)
[![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square)](https://github.com/Baka-SU/BakaSU)
[![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)](https://gitlab.com/simonpunk/susfs4ksu)

</div>

## Deskripsi Proyek

Repository ini menyediakan alur kerja (*workflow*) cloud build Actions untuk menghasilkan paket instalasi AnyKernel3 berdasarkan KMI GKI Android dan level security patch. Build standar menggunakan BakaSU sekaligus memungkinkan Anda mengaktifkan opsi fitur tambahan lainnya secara mandiri di konfigurasi *workflow*; Anda juga dapat memilih *Clean build* untuk menghasilkan kernel yang tidak mengintegrasikan KernelSU, SUSFS, maupun patch fitur opsional.

Versi kernel dan revisi rilis dibaca dari matriks JSON di bawah `data/android*/`, dan diperbarui secara berkala oleh *workflow* sinkronisasi data.

## Pemberitahuan Penting

Baru-baru ini kami melakukan refaktorisasi besar-besaran, yang mengakibatkan peningkatan drastis pada langkah build dan artefak. Hal ini membuat waktu pengerjaan *workflow* build kernel yang mencakup seluruh versi kernel menjadi sangat lama. Oleh karena itu, kami tidak lagi menjalankan build dan rilis (*Release*) untuk seluruh versi kernel secara berkala setiap kali ada pembaruan besar pada BakaSU.

Langkah ini bertujuan untuk mengurangi penggunaan jangka panjang sumber daya publik GitHub Actions. Setiap pengguna disarankan untuk melakukan *fork* repository ini dan membangun sendiri kernel tunggal di repository *fork* tersebut agar sama persis dengan versi kernel yang dibutuhkannya, sehingga sangat mengurangi fenomena penyalahgunaan daya komputasi. Atas ketidaknyamanan ini kami mohon maaf. Untuk detail mengenai cara menggunakan *workflow* repository ini beserta repository *fork*-nya, silakan lihat bagian terkait di `README.md`.

## KMI yang Didukung

| Android KMI | Seri Kernel | Pilihan `build_target` |
|---|---|---|
| Android 12 | 5.10 | `android12-5.10` |
| Android 13 | 5.10 | `android13-5.10` |
| Android 13 | 5.15 | `android13-5.15` |
| Android 14 | 5.15 | `android14-5.15` |
| Android 14 | 6.1 | `android14-6.1` |
| Android 15 | 6.6 | `android15-6.6` |
| Android 16 | 6.12 | `android16-6.12` |
| Android 17 | 6.18 | `android17-6.18` |

Versi 5.10 dan 5.15 sama-sama bersesuaian dengan beberapa KMI Android. Khususnya pada Android 13 dan Android 14 yang memiliki versi kernel yang sama untuk 5.15, KMI tidak dapat ditentukan secara otomatis hanya berdasarkan `5.15.xxx`; saat melakukan build dengan versi spesifik, Anda harus memilih versi Android yang sesuai secara manual. Kernel Android 17 / 6.18 saat ini telah mendukung build dasar, sementara beberapa komponen pendukung akan dilewati otomatis sesuai status dukungan hulunya (*upstream*).

## Menjalankan Build

1. Buka halaman [Actions](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions) di repository Anda, pilih *workflow* **Build Kernel** (*构建内核*), lalu klik **Run workflow**.
2. Pada `build_target`, pilih salah satu KMI atau pilih `all` untuk membangun seluruh target. Pilihan ini berupa opsi tunggal (*single choice*); jika Anda ingin membangun beberapa target tetapi tidak semuanya, jalankan masing-masing target secara terpisah.
3. Atur opsi fitur (*feature options*) dan `release_type` sesuai kebutuhan, lalu jalankan *workflow*.
4. Setelah build selesai, unduh artefak (*Artifacts*) dari halaman detail eksekusi; Anda juga dapat mengunduhnya dari halaman *Releases* saat membuat *Release*.

### Penyaringan Berdasarkan Versi Kernel

Setelah mengaktifkan `build_kernel_version`, penyaringan versi akan diprioritaskan di atas tombol versi biasa. `kernel_version_filter` menerima versi lengkap atau wildcard seri:

| Masukan | Fungsi |
|---|---|
| `6.6.66` | Membangun `6.6.66` dari data versi KMI terkait |
| `6.6.X` atau `6.6.x` | Membangun seluruh sub-versi `6.6` dalam data KMI |

Aturan Pemilihan:

- 5.10: `kernel_android_version` wajib memilih `android12` atau `android13`.
- 5.15: Wajib memilih `android13` atau `android14`.
- 6.1, 6.6, 6.12, 6.18: *Workflow* masing-masing menggunakan KMI Android 14, 15, 16, dan 17, tanpa perlu pemilihan manual.

Level *patch*, revisi rilis (*release revision*), dan versi LTS dibaca dari data JSON terkait. Build versi tertentu tidak akan membuat GitHub Release, meskipun `release_type` dipilih sebagai *pre-release* atau rilis resmi.

### Jenis Rilis (Release Types)

Pilihan `release_type` untuk build versi biasa:

- `Actions`: Hanya menyimpan artefak eksekusi Actions, tidak membuat Release. Nilai default.
- `Pre-Release`: Membuat prarilis (*pre-release*) setelah build berhasil di repository ini.
- `Release`: Membuat rilis resmi setelah build berhasil di repository ini.

Repository *fork* hanya menghasilkan artefak Actions dan tidak akan mempublikasikan Release ke repository hulu (*upstream*).

## Cabang BakaSU (BakaSU Branch)

Ketika `kernelsu_branch` dikosongkan, maka `main` yang akan digunakan. Anda juga dapat mengisi nama cabang jarak jauh (*remote branch*) BakaSU, atau commit SHA 40-digit lengkap. *Workflow* akan mengurai dan mengunci commit yang sesuai dengan cabang tersebut pada awal build, sehingga setiap KMI dalam eksekusi yang sama menggunakan kode yang sama; catatan rilis akan menautkan ke commit BakaSU yang benar-benar di-build.

## Fitur Build Opsional

| Opsi | Keterangan |
|---|---|
| `clean_build` | Tidak mengintegrasikan BakaSU, SUSFS, dan patch fitur opsional. |
| `cancel_susfs` | Mematikan integrasi SUSFS. SUSFS diaktifkan secara default; Android 17 / 6.18 belum memiliki cabang hulu dan akan dilewati secara otomatis. |
| `use_zram` | Mengaktifkan peningkatan ZRAM (LZ4KD). Android 17 / 6.18 belum memiliki patch terkait dan akan dilewati secara otomatis. |
| `use_bbg` | Mengaktifkan patch anti-reboot/anti-brick BBG. |
| `use_rekernel` | Mengaktifkan driver Re-Kernel, fitur masih dalam tahap pengujian. Untuk sementara dilewati pada Android 17 / 6.18 sampai repository ini beradaptasi dengan tata letak sumber baru hulu. |
| `cve_2026_43499_patch` | Menerapkan rantai perbaikan CVE-2026-43499, aktif secara default; 6.18 belum memiliki patch adaptasi di repository ini dan akan dilewati secara otomatis. |
| `build_bypass` | Membangun Bypass Image tambahan, yang disertakan dalam paket instalasi bersama Image biasa. |
| `droidspaces` | Memilih patch container Droidspaces: `off`, `678`, `123`, atau `345`. Versi 6.12 ke atas menggunakan patch generik hulu. |
| `droidspaces_ntsync` | Mengaktifkan NTSync dalam kombinasi yang didukung, mengharuskan Droidspaces diaktifkan secara bersamaan. Saat ini belum ada patch Android 17 / 6.18, kombinasi ini akan dilewati secara otomatis. |

Mode Bypass digunakan untuk menyelidiki masalah kompatibilitas versi modul kernel, bukan untuk melewati deteksi root. Saat diaktifkan, kompilasi penuh kedua akan dilakukan, yang menambah waktu build. Ikuti petunjuk skrip instalasi untuk memilih Image biasa atau Bypass Image saat melakukan flashing.

Patch Droidspaces bersifat eksperimental, perangkat dan versi kernel yang berbeda mungkin perlu mencoba slot yang berbeda. Android 16 / 6.12 dan Android 17 / 6.18 hanya memiliki satu jenis patch slot, pilih nilai apa pun selain `off`. Hulu kekurangan patch kompatibilitas NTSync untuk Android 14 / 5.15; kombinasi ini akan menyebabkan build gagal, harap tetap mematikannya. Android 17 / 6.18 akan otomatis melewati jika patch NTSync tidak ada.

## Artefak Build

Nama artefak mencakup KMI Android, versi kernel lengkap, dan level security patch OS; revisi hulu juga akan disertakan jika ada. Contoh:

android14-5.15.148-2024-05-r25-BakaSU-AnyKernel3.zip

Setelah mengaktifkan Bypass, paket instalasi akan mencakup `Image` biasa dan `Bypass-Image`. Pilih artefak yang sesuai dengan KMI Android dan cabang kernel perangkat Anda; lakukan *backup* image boot bawaan sebelum melakukan flashing, dan pastikan perangkat Anda memiliki metode pemulihan (*recovery*) yang berfungsi.

## Stock Config

Jika `config/stock_defconfig` ada di repository, build akan otomatis menggunakannya untuk penyamaran konfigurasi `/proc/config.gz`; jika file tidak ada, langkah ini dilewati. Anda dapat mengekstrak `/proc/config.gz` dari kernel resmi perangkat saat ini, mendekompresinya, meletakkannya di direktori ini, dan menamainya `stock_defconfig`.

## Sinkronisasi Data GKI

Workflow [Perbarui Data Versi GKI](.github/workflows/update-gki-data.yml) berjalan otomatis setiap hari Senin pukul UTC 08:00, dan juga dapat dipicu secara manual. Workflow menjalankan tes sinkronisasi, memperbarui JSON, memvalidasi matriks build, dan melakukan commit perubahan data.

## Ucapan Terima Kasih

- [zzh20188](https://github.com/zzh20188): Penulis repository build GKI hulu sebelumnya. Repository ini sekarang telah terpisah dari jaringan fork, dan zzh20188/GKI_KernelSU_SUSFS bukan lagi repository hulu untuk repository ini.
- [coolzyd9107](https://github.com/coolzyd9107): Pemelihara repository ini.
- [zhuzhuzihan](https://github.com/zhuzhuzihan): Perbaikan workflow serta pengembangan & pemeliharaan Telegram Bot.
- [TanakaLun](https://github.com/TanakaLun): Perbaikan workflow dan peningkatan fitur.
- [YC酱luyancib](https://github.com/luyanci): Telegram Bot dan saran alur kerja build.
- [AlexLiuDev233](https://github.com/AlexLiuDev233): Perbaikan bug workflow.
- [cctv18](https://github.com/cctv18): Workflow, dukungan 6.12, dan saran perbaikan masalah SUSFS.

Untuk build baru dan pemberitahuan perubahan penting, lihat [Saluran Telegram](https://t.me/BakaSUKernelBuilds); untuk saluran resmi BakaSU, lihat [BakaSU_Grp](https://t.me/BakaSU_Grp).
