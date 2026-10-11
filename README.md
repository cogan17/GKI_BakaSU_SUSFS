[**简体中文**](README.md) | [English](README.en.md) | [Bahasa Indonesia](README.id.md)

# GKI BakaSU SUSFS · Cogan Fork

> 基于 **[coolzyd9107 原项目](https://github.com/coolzyd9107/GKI_BakaSU_SUSFS)** 的独立派生版本，由 **[Cogan](https://github.com/cogan17)** 维护。此仓库**不是上游官方仓库**。

[![Release](https://img.shields.io/github/v/release/cogan17/GKI_BakaSU_SUSFS?include_prereleases&label=Release)](https://github.com/cogan17/GKI_BakaSU_SUSFS/releases)
[![Custom Build](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/workflows/kernel-custom.yml/badge.svg)](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/workflows/kernel-custom.yml)
[![License](https://img.shields.io/github/license/cogan17/GKI_BakaSU_SUSFS)](LICENSE)

<a href="https://t.me/CoganKernel"><img alt="Telegram Channel" src="https://img.shields.io/badge/TELEGRAM-%40CoganKernel-2596BE?logo=telegram&amp;logoColor=white" height="26"></a> <a href="https://t.me/CoganKernelGp"><img alt="Telegram Group" src="https://img.shields.io/badge/GROUP-%40CoganKernelGp-2596BE?logo=telegram&amp;logoColor=white" height="26"></a>

**快速入口：** [Actions](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions) · [自定义构建](.github/workflows/kernel-custom.yml) · [主构建工作流](.github/workflows/main.yml) · [手动发布](.github/workflows/manual-release.yml) · [Releases](https://github.com/cogan17/GKI_BakaSU_SUSFS/releases)

## Cogan 内核的优势

Cogan 注重**可追溯的构建与多层兼容性检查**，而不只是成功编译内核。这些措施属于工作流保护，**不能保证完全避免 bootloop、kernel panic 或设备变砖**。

- **构建前兼容性检查：**核对 Android GKI/KMI 组合、固定的源码提交、内核配置以及上游兼容性保护；发现不匹配时停止构建（*fail closed*）。
- **配套的 BakaSU 管理器与内核：**从与内核驱动**相同 BakaSU 提交**的官方构建获取 normal 和 spoofed 管理器 APK，并检查版本信息、内核接受的签名证书及 arm64 `ksud`。
- **固定 NoMount 来源：**内核驱动与 metamodule/userspace 使用同一选定的 NoMount 提交，并检查软件包与源码身份。
- **可追溯的构建产物：**提供 AnyKernel3 刷入 ZIP、配套 APK、按需提供 NoMount metamodule，以及记录提交、来源、版本和校验和的 `*-bundle.json`；仅在构建和检查成功后提供相关文件。
- **发布保护：**Manual Release From Run 在发布前检查文件完整性和齐全性，不会暗中混用不同版本的组件。
- **便于排查的失败报告：**GitHub Actions Summary 提供检查结果、技术证据和多语言报告，方便定位问题并与上游开发者沟通。

**SUSFS 状态：**只要 BakaSU 上游仍禁止当前 SUSFS 组合，兼容性检查便会终止构建。不要为了生成 ZIP 而绕过这一保护。CI 通过也不能替代真机测试和可靠的恢复方案。

## 项目说明

本仓库通过 GitHub Actions 构建 Android GKI 内核，以 **BakaSU + SUSFS** 为基础，并提供 NoMount、ZRAM、BBG、Re-Kernel 等可选功能。成功构建后可下载 **AnyKernel3 ZIP**；`clean_build` 用于不集成 BakaSU、SUSFS 和可选补丁的构建。

**GKI/KMI 不等于手机运行的 Android 系统版本。** 例如，运行 Android 16 的设备可能使用 Android 14 GKI / Linux 6.1，具体取决于设备的实际 KMI。刷入前必须核对 KMI、原厂内核和设备兼容性，不能只看 Android 系统版本。

## 重要通知

这是 **Cogan 个人维护的派生仓库**。中文原始说明来自 [coolzyd9107/GKI_BakaSU_SUSFS](https://github.com/coolzyd9107/GKI_BakaSU_SUSFS)；本仓库新增了适用于 Cogan 的版本显示、工作流与发布改进。请勿将此分支的发布说明误认为上游官方公告。

**支持范围：** Android 17 / 6.18 目前仅提供有限功能，部分上游尚未支持的组件会被跳过。5.10、5.15 存在多个 Android KMI，必须选择正确的 KMI。

## 支持的 KMI

| Android KMI | 内核系列 | `build_target` 选项 |
|---|---|---|
| Android 12 | 5.10 | `android12-5.10` |
| Android 13 | 5.10 | `android13-5.10` |
| Android 13 | 5.15 | `android13-5.15` |
| Android 14 | 5.15 | `android14-5.15` |
| Android 14 | 6.1 | `android14-6.1` |
| Android 15 | 6.6 | `android15-6.6` |
| Android 16 | 6.12 | `android16-6.12` |
| Android 17 | 6.18 | `android17-6.18` |

5.10 和 5.15 都对应多个 Android KMI。尤其 5.15 的 Android 13 与 Android 14 存在相同的内核版本号，不能仅凭 `5.15.xxx` 自动判断 KMI；指定版本构建时必须手动选择对应的 Android 版本。Android 17 / 6.18 当前已支持基础构建，部分附属组件按上游支持状态自动跳过。

## 运行构建

### 1. Android Kernel Build - Custom（推荐）

1. 打开 **[Custom Build](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/workflows/kernel-custom.yml)**，选择 `main` → **Run workflow**。
2. 设置 `android_version`、`kernel_version`、`sub_level`、`os_patch_level`（例如 `lts`）及 `revision`。
3. 可填写 `version`（例如 `Cogan`）、`kernelsu_branch`（留空使用 BakaSU 默认分支）和 `build_time`（`N` 或留空为当前 UTC 时间）。
4. 按设备需求选择功能，运行构建，成功后在该 run 的 **Artifacts** 下载 `*-AnyKernel3.zip`。

**Cogan r7 示例：** `android14` / `6.1` / `177` / `lts` / `r7`，自定义名称 `Cogan`。此配置不是所有设备通用的刷机方案。

### 2. Build Kernel（矩阵 / 版本筛选）

在 **[Build Kernel](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/workflows/main.yml)** 中，`build_target` 可选择单个 KMI 或 `all`；也可启用 `build_kernel_version`，输入 `6.6.66` 或 `6.6.X` 等条件。5.10/5.15 还必须选择对应的 `kernel_android_version`。

**注意：** 主工作流的 `build_time` 仍有旧默认值；希望使用当前 UTC 时间时，请手动填入 `N`。Custom Build 的默认值已经是 `N`。

### 3. Manual Release From Run

**[Manual Release From Run](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/workflows/manual-release.yml)** 可将成功 run 的原始 AnyKernel3 ZIP 发布到 Releases：

1. 在 `main` 运行此工作流。
2. 输入成功构建的数字 `source_run_id`，选择 `Pre-Release` 或 `Release`。
3. 工作流检查来源、ZIP 完整性和必需文件后，将原始 ZIP 上传至 GitHub Release；无需重新打包。

**重要：** 主工作流自带的自动发布任务目前仅针对其他仓库启用，在 Cogan 分支请使用上述 Manual Release。实例：r7 的 [Run 38020806221](https://github.com/cogan17/GKI_BakaSU_SUSFS/actions/runs/38020806221) → [Cogan r7 Release](https://github.com/cogan17/GKI_BakaSU_SUSFS/releases/tag/BakaSU-run-38020806221)。

## BakaSU 分支

`kernelsu_branch` 留空时使用 `main`。也可以填写 BakaSU 的远程分支名，或完整的 40 位 commit SHA。工作流会在构建开始时解析并固定该分支对应的提交，因此同一次运行的各个 KMI 使用相同代码；发布说明会链接到实际构建的 BakaSU 提交。

## 可选构建功能

| 选项 | 说明 |
|---|---|
| `clean_build` | 不集成 BakaSU、SUSFS 及可选功能补丁。 |
| `cancel_susfs` | 关闭 SUSFS 集成。默认启用 SUSFS；Android 17 / 6.18 暂无上游分支，会自动跳过。 |
| `use_zram` | 启用 ZRAM 增强（LZ4KD）。Android 17 / 6.18 暂无对应补丁，会自动跳过。 |
| `use_bbg` | 启用 BBG 防格机补丁。 |
| `use_rekernel` | 启用 Re-Kernel 驱动，功能仍在测试。Android 17 / 6.18 暂时跳过，待本仓库适配上游新源码布局。 |
| `cve_2026_43499_patch` | 应用 CVE-2026-43499 修复链，默认开启；6.18 暂无本仓库适配补丁，会自动跳过。 |
| `build_bypass` | 额外构建 Bypass Image，与普通 Image 一起放入安装包。 |
| `droidspaces` | 选择 Droidspaces 容器补丁：`off`、`678`、`123` 或 `345`。6.12 及以上使用上游的通用补丁。 |
| `droidspaces_ntsync` | 在支持的组合中启用 NTSync，需同时启用 Droidspaces。当前没有 Android 17 / 6.18 补丁，该组合会自动跳过。 |
| `use_nomount` | NoMount 集成。**当前限制：** 可复用构建工作流在非 clean 构建中仍会执行 NoMount 安装步骤，即使此开关设为 `false`。修复前请勿依靠开关关闭该功能。 |

**版本显示：** 对 Android 14 GKI / Linux 6.1 的自定义名称，Cogan 已缩短在 HyperOS Settings 中显示的编译器信息，同时尽量保留版本解析结构。自动 UTC 构建时间使用 `YYYY-MM-DD HH:mm:ss UTC`；不同设备的 Settings 可能略有差异。


Bypass 模式用于排查内核模块版本兼容问题，不用于绕过 root 检测。启用后会进行第二次完整编译，并增加构建时间。刷入时按安装脚本提示选择普通 Image 或 Bypass Image。

Droidspaces 补丁具有实验性，不同设备和内核版本可能需要尝试不同槽位。Android 16 / 6.12 和 Android 17 / 6.18 只有一种槽位补丁，选任一非 `off` 值即可。上游没有 Android 14 / 5.15 的 NTSync 兼容补丁；该组合会使构建失败，请保持关闭。Android 17 / 6.18 的 NTSync 补丁缺失时会自动跳过。

## 构建产物

成功的 Custom Build 直接提供可刷入的 `*-AnyKernel3.zip`，不再需要对当前版本的 artifact 进行二次 ZIP 解包或重新打包。启用 `build_bypass` 时，包内也可能包含额外的 `Bypass-Image`。

### Cogan r7 测试记录

- **内核：** `6.1.177-android14-11-Cogan`（Android 14 GKI / 6.1.177 LTS）。
- **测试设备：** Xiaomi 14T Pro（`2407FPN8EG`），Android 16 / HyperOS。
- **已验证：** GitHub Actions 编译及打包成功、HyperOS 内核版本正常显示（不再为 `Unavailable`）、BakaSU 与内置 NoMount 在管理器中可识别。
- **未验证：** 所有可选补丁的完整运行效果及其他设备/ROM 的兼容性。

**刷入前：** 核对设备的实际 KMI，备份 boot 及安装流程可能修改的其他分区，并确保能够恢复原厂镜像。使用与设备兼容的内核刷入工具；风险由用户自行承担。

## Stock Config

若仓库中存在 `config/stock_defconfig`，构建会自动将其用于 `/proc/config.gz` 配置伪装；文件不存在时跳过此步骤。可以从设备当前官方内核取得 `/proc/config.gz`，解压后放入该目录并命名为 `stock_defconfig`。

## GKI 数据同步

[更新 GKI 版本数据](.github/workflows/update-gki-data.yml)工作流每周一 UTC 08:00 自动运行，也可以手动触发。工作流会运行同步测试、更新 JSON、验证构建矩阵，并提交数据变更。

## 配套管理器、内核与 NoMount

BakaSU 构建会提供官方普通版和 spoofed 版管理器 APK、AnyKernel3 内核 ZIP，
以及启用 `use_nomount` 时的 NoMount 元模块 ZIP。两个 APK 保持官方签名，
来自与内核驱动**同一提交**的最终 `Build Manager` 产物；构建会检查版本号、
内核接受的官方证书以及 arm64 `ksud`。

NoMount 驱动和用户空间/元模块使用同一个固定的 `dev` 提交。此元模块仅适用于
内置 NoMount（`CONFIG_NOMOUNT=y`），不包含 LKM。安装一个管理器 APK，刷入
配套内核并重启，然后通过 BakaSU 安装 NoMount 并再次重启。构建检查不代替真机测试。

如指定提交没有完整且未过期的官方 APK，构建会在编译前停止，不会静默替换版本。
`*-bundle.json` 记录源码提交、版本、APK 来源和校验值。
**Manual Release From Run** 校验完整性后发布指定运行中的原始配套文件，支持多个
内核；旧运行仍可发布内核，但会明确标注缺少配套管理器和元模块。

## 致谢

- **原项目、主要开发者：** [coolzyd9107 / GKI_BakaSU_SUSFS](https://github.com/coolzyd9107/GKI_BakaSU_SUSFS)。
- **本派生仓库的维护及修改：** [Cogan（cogan17）](https://github.com/cogan17)。
- **项目历史与贡献者：** [zzh20188](https://github.com/zzh20188)、[zhuzhuzihan](https://github.com/zhuzhuzihan)、[TanakaLun](https://github.com/TanakaLun)、[luyancib](https://github.com/luyancib)、[AlexLiuDev233](https://github.com/AlexLiuDev233)、[cctv18](https://github.com/cctv18)。
- 感谢 **BakaSU、KernelSU、SUSFS、NoMount、Re-Kernel、AnyKernel3** 与 Android GKI 的开发者及贡献者。

本仓库采用 **GPL-2.0** 许可证。[上游 Telegram 频道](https://t.me/BakaSUKernelBuilds) 属于原项目社区资源，并非 Cogan 分支专用支持频道。
