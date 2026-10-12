#!/usr/bin/env python3
"""Stage one validated Re-Kernel layout for Cogan's in-tree GKI build.

No network access and no flashing. Unknown/duplicate layouts are rejected.
"""
import argparse
from pathlib import Path
import re
import shutil
import sys

SPLIT_C = (
    "rekernel_main.c", "rekernel_netlink.c", "rekernel_binder.c",
    "rekernel_signal.c", "rekernel_netfilter.c",
)
SPLIT_HEADERS = ("rekernel.h", "rekernel_internal.h")
LEGACY_FILES = ("rekernel.c", "rekernel.h")
REGISTER = 'obj-$(CONFIG_REKERNEL) += rekernel/'
SOURCE = 'source "drivers/rekernel/Kconfig"'


def layout(source):
    if not source.is_dir():
        raise ValueError("Re-Kernel LKM-Source directory missing")
    actual_c = {p.name for p in source.glob("rekernel*.c")}
    if actual_c == {"rekernel.c"} and all((source / name).is_file() for name in LEGACY_FILES):
        return "legacy", LEGACY_FILES
    if actual_c == set(SPLIT_C) and all((source / name).is_file() for name in SPLIT_C + SPLIT_HEADERS):
        return "split", SPLIT_C + SPLIT_HEADERS
    raise ValueError("Unsupported, incomplete, or mixed Re-Kernel source layout")


def stage(source, common, defconfig, version):
    if not re.fullmatch(r"(?:5\.10|5\.15|6\.1|6\.6|6\.12)", version):
        raise ValueError("Unsupported Re-Kernel GKI series")
    kind, names = layout(source)
    drivers = common / "drivers"
    dest = drivers / "rekernel"
    tree_kconfig, tree_makefile = drivers / "Kconfig", drivers / "Makefile"
    if dest.exists():
        raise ValueError("Re-Kernel already integrated: refusing duplicate driver")
    if not all(p.is_file() for p in (tree_kconfig, tree_makefile, defconfig)):
        raise ValueError("Missing kernel integration file or defconfig")

    menu = tree_kconfig.read_text()
    makefile = tree_makefile.read_text()
    config = defconfig.read_text()
    if SOURCE in menu or REGISTER in makefile or re.search(r"^CONFIG_REKERNEL=", config, re.M):
        raise ValueError("Existing Re-Kernel registration/configuration: refusing duplicate")
    if not re.search(r"^endmenu\s*$", menu, re.M):
        raise ValueError("Unknown drivers/Kconfig menu structure")
    if kind == "legacy" and "struct proc_ops" not in (common / "include/linux/proc_fs.h").read_text():
        raise ValueError("Legacy proc_ops adaptation unsupported by this kernel")

    dest.mkdir(parents=True)
    for name in names:
        shutil.copy2(source / name, dest / name)
    if kind == "legacy":
        code = (dest / "rekernel.c").read_text()
        code = code.replace("struct file_operations", "struct proc_ops")
        code = re.sub(r"(?m)^[ \t]*\.owner\s*=\s*THIS_MODULE,\s*\n", "", code)
        for old, new in (
            (".unlocked_ioctl =", ".proc_ioctl ="),
            (".compat_ioctl =", ".proc_compat_ioctl ="),
            (".release =", ".proc_release ="),
            (".llseek =", ".proc_lseek ="),
            (".write =", ".proc_write ="),
            (".read =", ".proc_read ="),
            (".open =", ".proc_open ="),
        ):
            code = code.replace(old, new)
        code = code.replace("#include <../android/binder_internal.h>",
                            '#include "../../drivers/android/binder_internal.h"')
        if "#include <linux/seq_file.h>" not in code:
            code = "#include <linux/seq_file.h>\n" + code
        (dest / "rekernel.c").write_text(code)
        header = dest / "rekernel.h"
        macro = "KERNEL_" + version.replace(".", "_")
        header.write_text(header.read_text().replace("// #define " + macro,
                                                      "#define " + macro))
    else:
        binder = dest / "rekernel_binder.c"
        code = binder.read_text()
        original_include = "#include <../android/binder_internal.h>"
        if original_include not in code and \
                '#include "../../drivers/android/binder_internal.h"' not in code:
            raise ValueError("Unknown Binder include layout; manual review required")
        binder.write_text(code.replace(original_include,
                         '#include "../../drivers/android/binder_internal.h"'))

    (dest / "Kconfig").write_text(
        'menu "Re:Kernel"\n'
        'config REKERNEL\n'
        '    bool "Re:Kernel in-tree support (experimental)"\n'
        '    default n\n'
        'config REKERNEL_NETWORK\n'
        '    bool "Re:Kernel network support"\n'
        '    depends on REKERNEL\n'
        '    default n\n'
        'config REKERNEL_LEGACY_NETLINK\n'
        '    bool "Re:Kernel legacy transport"\n'
        '    depends on REKERNEL\n'
        '    default n\n'
        'endmenu\n'
    )
    objects = "rekernel-y := " + " ".join(n[:-2] + ".o" for n in SPLIT_C) + "\n"
    (dest / "Makefile").write_text(
        'obj-$(CONFIG_REKERNEL) += rekernel.o\n'
        + (objects if kind == "split" else "")
        + 'ccflags-$(CONFIG_REKERNEL_NETWORK) += -DNETWORK_FILTER\n'
        + 'ccflags-$(CONFIG_REKERNEL_LEGACY_NETLINK) += -DLEGACY_NETLINK\n'
    )
    # Insert exactly once in the final drivers menu; never duplicate on repeat.
    last_menu = list(re.finditer(r"(?m)^endmenu\s*$", menu))[-1]
    menu = menu[:last_menu.start()] + SOURCE + "\n" + menu[last_menu.start():]
    tree_kconfig.write_text(menu)
    tree_makefile.write_text(makefile.rstrip("\n") + "\n" + REGISTER + "\n")
    with defconfig.open("a") as out:
        out.write("CONFIG_REKERNEL=y\nCONFIG_REKERNEL_NETWORK=y\n")
    print("Cogan Re-Kernel staged:", kind, "| objects:", len(SPLIT_C) if kind == "split" else 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--common", type=Path, required=True)
    p.add_argument("--defconfig", type=Path, required=True)
    p.add_argument("--kernel-version", required=True)
    a = p.parse_args()
    try:
        stage(a.source, a.common, a.defconfig, a.kernel_version)
    except (ValueError, OSError, UnicodeError) as exc:
        print("::error title=Re-Kernel compatibility::" + str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
