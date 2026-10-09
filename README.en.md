[中文](README.md) | [English](README.en.md) | [Bahasa Indonesia](README.id.md)
<div align="center">

GKI BakaSU SUSFS

Build Android GKI kernels with GitHub Actions, integrated with BakaSU and SUSFS.

![Release](https://img.shields.io/github/v/release/coolzyd9107/GKIBakaSUSUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f) ![Kernel Build](https://github.com/zhuzhuzihan/GKIBakaSUSUSFS/actions/workflows/main.yml/badge.svg) ![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc) ![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square) ![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)

</div>

简体中文 | English | Bahasa Indonesia

Project Overview

This repository provides a cloud-based GitHub Actions workflow for building Android GKI kernels and packaging them as AnyKernel3 flashable ZIPs according to the Android GKI KMI and security patch level.

Standard builds integrate BakaSU. Additional optional features can be enabled through workflow settings. You can also select Clean build to build a kernel without KernelSU, SUSFS, or optional feature patches.

Kernel versions and release revisions are retrieved from JSON matrices under data/android*/. These data files are periodically updated by the data synchronization workflow.

Important Notice

Following a major restructuring, the number of build steps and generated artifacts has increased significantly. Building and releasing every supported kernel version now takes an excessive amount of time.

Therefore, we will no longer routinely run builds and publish releases for all kernel versions, including after major BakaSU updates. This change is intended to reduce prolonged consumption of GitHub Actions public runner resources and discourage excessive use of computing resources.

Users are encouraged to fork this repository and build only the specific kernel version they need in their own fork. This significantly reduces build time and resource consumption.

We apologize for any inconvenience. Please refer to the relevant sections of this README for instructions on using the original repository and forked repositories.

Supported KMI Targets
Android KMI	Kernel Series	build_target Option
Android 12	5.10	android12-5.10
Android 13	5.10	android13-5.10
Android 13	5.15	android13-5.15
Android 14	5.15	android14-5.15
Android 14	6.1	android14-6.1
Android 15	6.6	android15-6.6
Android 16	6.12	android16-6.12
Android 17	6.18	android17-6.18

Kernel series 5.10 and 5.15 correspond to multiple Android KMI targets. In particular, Android 13 and Android 14 both use kernel series 5.15, so the KMI cannot be determined from a version number such as 5.15.xxx alone. When building a specific version, you must manually select the correct Android version.

Android 17 / 6.18 currently supports basic builds. Some auxiliary components are automatically skipped depending on upstream support.

Running a Build
Open the repository's Actions page.
Select the Build Kernel workflow and click Run workflow.
Choose a KMI target under build_target, or select all to build every target. This is a single-choice option. To build multiple targets without building all of them, run the workflow separately for each target.
Configure the optional features and release_type as needed.
Start the workflow.
Once the build finishes, download the artifacts from the run's Artifacts section. If a Release was created, the packages can also be downloaded from the Releases page.
Filtering by Kernel Version

Enable build_kernel_version to filter builds by kernel version. This filter takes precedence over the regular version-selection options.

The kernel_version_filter parameter accepts either a complete version number or a kernel-series wildcard.

Input	Description
6.6.66	Build version 6.6.66 from the selected KMI's version data
6.6.X or 6.6.x	Build all 6.6 patch versions available in the selected KMI's data

Selection rules:

5.10: Set kernel_android_version to android12 or android13.
5.15: Set kernel_android_version to android13 or android14.
6.1, 6.6, 6.12, and 6.18: The workflow automatically uses the corresponding Android 14, 15, 16, and 17 KMI targets. Manual Android version selection is unnecessary.

The patch level, release revision, and LTS version are obtained from the corresponding JSON data.

A build filtered to a specific kernel version will not create a GitHub Release, even if release_type is set to pre-release or release.

Release Types

For regular builds, release_type supports the following options:

Actions: Keep the build artifacts in GitHub Actions without creating a Release. This is the default.
Pre-Release: Create a pre-release after a successful build in the original repository.
Release: Create a full release after a successful build in the original repository.

Forked repositories only generate Actions artifacts and will not publish Releases to the upstream repository.

BakaSU Branch

If kernelsu_branch is left empty, the workflow uses main.

You can also specify a remote BakaSU branch name or a full 40-character commit SHA. At the beginning of the build, the workflow resolves the selected branch to a specific commit and pins it for the entire run. This ensures that all KMI targets in the same run use the same BakaSU source revision.

The release notes include a link to the actual BakaSU commit used for the build.

Optional Build Features
Option	Description
clean_build	Build without BakaSU, SUSFS, or optional feature patches.
cancel_susfs	Disable SUSFS integration. SUSFS is enabled by default. Android 17 / 6.18 automatically skips it because no upstream branch is currently available.
use_zram	Enable ZRAM enhancements using LZ4KD. Automatically skipped on Android 17 / 6.18 because the corresponding patches are unavailable.
use_bbg	Enable the BBG anti-brick patch.
use_rekernel	Enable the Re-Kernel driver. This feature is still experimental. Android 17 / 6.18 skips it temporarily while this repository adapts to the upstream source layout.
cve_2026_43499_patch	Apply the CVE-2026-43499 fix chain. Enabled by default. Automatically skipped on 6.18 because an adapted patch is not yet available in this repository.
build_bypass	Build an additional Bypass Image and include it alongside the regular Image in the installation package.
droidspaces	Select the Droidspaces container patch: off, 678, 123, or 345. Android 16 / 6.12 and newer use the upstream generic patch.
droidspaces_ntsync	Enable NTSync for supported configurations. Droidspaces must also be enabled. Automatically skipped on Android 17 / 6.18 because the required patch is unavailable.

Bypass mode is intended for troubleshooting kernel module compatibility issues, not for bypassing root detection. Enabling it triggers a second full compilation and increases build time.

During installation, follow the installer script's instructions to select either the regular Image or the Bypass Image.

Droidspaces patches are experimental. Different devices and kernel versions may require testing different patch slots.

Android 16 / 6.12 and Android 17 / 6.18 support only one patch slot. Selecting any value other than off is sufficient.

The upstream source does not provide an NTSync compatibility patch for Android 14 / 5.15. Enabling this combination will cause the build to fail, so keep NTSync disabled for this target. On Android 17 / 6.18, NTSync is automatically skipped when its patch is unavailable.

Build Artifacts

Artifact filenames include the Android KMI, full kernel version, and OS security patch level. When an upstream revision is available, it is also included in the filename.

Example:

android14-5.15.148-2024-05-r25-BakaSU-AnyKernel3.zip


When Bypass mode is enabled, the package contains both Image and Bypass-Image.

Choose an artifact that matches your device's Android KMI and kernel branch. Before flashing, back up the stock Boot image and ensure that a recovery method is available in case anything goes wrong.

Stock Config

If config/stock_defconfig exists in the repository, the build automatically uses it for /proc/config.gz configuration spoofing. This step is skipped if the file is absent.

You can obtain /proc/config.gz from your device's current stock kernel, decompress it, and place the resulting configuration file at:

config/stock_defconfig

GKI Data Synchronization

The Update GKI Version Data workflow runs automatically every Monday at 08:00 UTC. It can also be triggered manually.

The workflow runs synchronization tests, updates the JSON data, validates the build matrix, and commits the resulting data changes.

Acknowledgments
zzh20188: Original author of the former upstream GKI build repository. This repository is no longer part of that fork network, and zzh20188/GKI_KernelSU_SUSFS is no longer its upstream repository.
coolzyd9107: Maintainer of this repository.
zhuzhuzihan: Workflow fixes and Telegram Bot development and maintenance.
TanakaLun: Workflow fixes and feature improvements.
YC酱luyancib: Telegram Bot and build process suggestions.
AlexLiuDev233: Workflow bug fixes.
cctv18: Workflow improvements, Android 6.12 support, and suggestions for fixing SUSFS issues.

For new build notifications and important updates, visit the Telegram channel.

For the official BakaSU community, visit BakaSU_Grp.
