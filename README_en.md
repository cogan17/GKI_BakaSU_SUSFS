[中文](README.md) | [English](README_en.md) | [Bahasa Indonesia](README_id.md)

<div align="center">

# GKI BakaSU SUSFS

Build Android GKI kernels based on GitHub Actions, integrating BakaSU and SUSFS.

[![Release](https://img.shields.io/github/v/release/coolzyd9107/GKI_BakaSU_SUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/releases)
[![Build Kernel](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml/badge.svg)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml)
[![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc)](https://t.me/BakaSUKernelBuilds)
[![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square)](https://github.com/Baka-SU/BakaSU)
[![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)](https://gitlab.com/simonpunk/susfs4ksu)

</div>

## Project Description

This repository provides Actions cloud build workflows to generate AnyKernel3 installation packages based on Android GKI KMI and security patch levels. Standard builds use BakaSU while allowing you to optionally enable other features in the workflow configuration; you can also select Clean build to generate a kernel without KernelSU, SUSFS, and optional feature patches.

Kernel versions and release revisions are read from the JSON matrix under `data/android*/`, and updated periodically by the data synchronization workflow.

## Important Notice

Recently we performed a major refactoring, which led to a drastic increase in build steps and artifacts, resulting in long execution times for kernel build workflows covering all kernel versions. Therefore, we will no longer regularly run kernel builds and releases for all versions whenever there is a major update to BakaSU.

This measure aims to reduce long-term consumption of GitHub Actions public resources. Each user is encouraged to fork this repository and independently build a single kernel matching their exact required kernel version in their forked repository, significantly reducing computational resource abuse. We apologize for any inconvenience caused. For details on how to use workflows in this repository and its forks, please refer to the relevant section in README.md.

## Supported KMI

| Android KMI | Kernel Series | `build_target` Option |
|---|---|---|
| Android 12 | 5.10 | `android12-5.10` |
| Android 13 | 5.10 | `android13-5.10` |
| Android 13 | 5.15 | `android13-5.15` |
| Android 14 | 5.15 | `android14-5.15` |
| Android 14 | 6.1 | `android14-6.1` |
| Android 15 | 6.6 | `android15-6.6` |
| Android 16 | 6.12 | `android16-6.12` |
| Android 17 | 6.18 | `android17-6.18` |

Both 5.10 and 5.15 correspond to multiple Android KMI. Especially for Android 13 and Android 14 which share the same kernel version for 5.15, KMI cannot be automatically determined solely by `5.15.xxx`; you must manually select the corresponding Android version when building a specified version. Android 17 / 6.18 currently supports basic builds, with some auxiliary components automatically skipped based on upstream support status.

## Running Builds

1. Open the repository's [Actions](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions) page, select the **Build Kernel** workflow and click **Run workflow**.
2. In `build_target`, select a KMI or choose `all` to build all targets. This is a single-choice option; if you need to build multiple targets but not all, run each target separately.
3. Set the feature options and `release_type` as needed, then start the workflow.
4. After the build completes, download artifacts from the run details page; you can also download them from the Releases page when creating a release.

### Filtering by Kernel Version

After enabling `build_kernel_version`, version filtering takes precedence over regular version switches. `kernel_version_filter` accepts full versions or series wildcards:

| Input | Function |
|---|---|
| `6.6.66` | Build `6.6.66` from the corresponding KMI version data |
| `6.6.X` or `6.6.x` | Build all `6.6` sub-versions in the KMI data |

Selection Rules:

- 5.10: `kernel_android_version` must be set to `android12` or `android13`.
- 5.15: Must be set to `android13` or `android14`.
- 6.1, 6.6, 6.12, 6.18: The workflows use Android 14, 15, 16, and 17 KMI respectively, no manual selection required.

Patch levels, release revisions, and LTS versions are read from the corresponding JSON data. Specifying a version build will not create a GitHub Release, even if `release_type` is set to pre-release or release.

### Release Types

Regular version build `release_type` options:

- `Actions`: Keep Actions run artifacts only, do not create a Release. Default.
- `Pre-Release`: Create a pre-release after a successful build in this repository.
- `Release`: Create an official release after a successful build in this repository.

Fork repositories only generate Actions artifacts and will not publish Releases to the upstream repository.

## BakaSU Branch

When `kernelsu_branch` is left blank, `main` is used. You can also enter a BakaSU remote branch name, or a full 40-character commit SHA. The workflow will resolve and lock in the commit corresponding to that branch at the start of the build, so each KMI in the same run uses the same code; release notes will link to the actually built BakaSU commit.

## Optional Build Features

| Option | Description |
|---|---|
| `clean_build` | Do not integrate BakaSU, SUSFS, and optional feature patches. |
| `cancel_susfs` | Disable SUSFS integration. SUSFS is enabled by default; Android 17 / 6.18 has no upstream branch yet and will be skipped automatically. |
| `use_zram` | Enable ZRAM enhancements (LZ4KD). Android 17 / 6.18 has no corresponding patch yet and will be skipped automatically. |
| `use_bbg` | Enable BBG anti-brick/anti-reboot patches. |
| `use_rekernel` | Enable Re-Kernel driver, features are still testing. Temporarily skipped on Android 17 / 6.18 until this repository adapts to upstream's new source layout. |
| `cve_2026_43499_patch` | Apply CVE-2026-43499 fix chain, enabled by default; 6.18 has no adaptation patch in this repository yet and will be skipped automatically. |
| `build_bypass` | Additionally build a Bypass Image, included in the installation package alongside the regular Image. |
| `droidspaces` | Select Droidspaces container patch: `off`, `678`, `123`, or `345`. 6.12 and above use upstream generic patches. |
| `droidspaces_ntsync` | Enable NTSync in supported combinations, requires Droidspaces to be enabled simultaneously. Currently no Android 17 / 6.18 patch available, this combination will be skipped automatically. |

Bypass mode is used to troubleshoot kernel module version compatibility issues, not to bypass root detection. When enabled, a second full compilation is performed, increasing build time. Follow the installation script prompt to choose between regular Image or Bypass Image when flashing.

Droidspaces patches are experimental, different devices and kernel versions may require trying different slots. Android 16 / 6.12 and Android 17 / 6.18 only have one slot patch type, select any non-`off` value. Upstream lacks NTSync compatibility patches for Android 14 / 5.15; this combination will cause the build to fail, please keep it disabled. Android 17 / 6.18 will automatically skip if the NTSync patch is missing.

## Build Artifacts

Artifact names include the Android KMI, full kernel version, and OS security patch level; upstream revisions will also be appended if present. For example:

```text
android14-5.15.148-2024-05-r25-BakaSU-AnyKernel3.zip

## Build Artifacts

After enabling Bypass, both the regular `Image` and `Bypass-Image` are included in the installation package. Choose artifacts matching your device's Android KMI and kernel branch; back up your original boot image before flashing, and ensure your device has a working recovery method.

## Stock Config

If `config/stock_defconfig` exists in the repository, the build will automatically use it for `/proc/config.gz` config masking; if the file does not exist, this step is skipped. You can extract `/proc/config.gz` from the device's current official kernel, decompress it, place it in this directory, and name it `stock_defconfig`.

## GKI Data Synchronization

The [Update GKI Version Data](.github/workflows/update-gki-data.yml) workflow runs automatically every Monday at UTC 08:00, and can also be triggered manually. The workflow runs sync tests, updates JSON, validates the build matrix, and commits data changes.

## Acknowledgments

- [zzh20188](https://github.com/zzh20188): Former upstream GKI build repository author. This repository has now separated from the fork network, and zzh20188/GKI_KernelSU_SUSFS is no longer the upstream repository for this repo.
- [coolzyd9107](https://github.com/coolzyd9107): Maintainer of this repository.
- [zhuzhuzihan](https://github.com/zhuzhuzihan): Workflow fixes and Telegram Bot development & maintenance.
- [TanakaLun](https://github.com/TanakaLun): Workflow fixes and feature improvements.
- [YC酱luyancib](https://github.com/luyanci): Telegram Bot and build workflow suggestions.
- [AlexLiuDev233](https://github.com/AlexLiuDev233): Workflow bug fixes.
- [cctv18](https://github.com/cctv18): Workflow, 6.12 support, and SUSFS issue fix suggestions.

For new builds and major change notifications, see the [Telegram Channel](https://t.me/BakaSUKernelBuilds); for the official BakaSU channel, see [BakaSU_Grp](https://t.me/BakaSU_Grp).
