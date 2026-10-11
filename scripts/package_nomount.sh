#!/usr/bin/env bash
# Build userspace from the very same checkout already integrated into the kernel.
set -euo pipefail
source_dir="$(realpath "$1")"
expected_commit="$2"
destination="$(realpath -m "$3")"
prefix="$4"
[[ "$expected_commit" =~ ^[0-9a-f]{40}$ ]]
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$expected_commit" ]]
git -C "$source_dir" diff --exit-code -- kernel userspace module
module_dir="$(mktemp -d "$RUNNER_TEMP/cogan-nomount.XXXXXX")"
trap 'rm -rf "$module_dir"' EXIT
cp -a "$source_dir/module/." "$module_dir/"
mkdir -p "$module_dir/bin" "$destination"
(
  cd "$source_dir/userspace/src"
  zig cc -target aarch64-linux -Oz -mcmodel=tiny -static -nostdlib \
    -ffreestanding -fno-unwind-tables -fno-ident -Wno-invalid-noreturn \
    -Wl,--entry=_start nm.c -o "$module_dir/bin/nm-arm64"
  zig cc -target arm-linux -Oz -static -nostdlib -ffreestanding \
    -fno-unwind-tables -fno-ident -Wno-invalid-noreturn \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -Wl,--entry=_start nm.c -o "$module_dir/bin/nm-arm"
)
chmod 0755 "$module_dir"/bin/nm-*
count="$(git -C "$source_dir" rev-list --count HEAD)"
sed -i "s/^versionCode=.*/versionCode=$count/; s/^version=.*/& (Cogan built-in $count-${expected_commit:0:8})/" "$module_dir/module.prop"
printf '%s\n' "$expected_commit" > "$module_dir/NOMOUNT_SOURCE_COMMIT"

# This distribution targets CONFIG_NOMOUNT=y only. Upstream's general installer
# unconditionally moves lkmloader before detecting built-in support, so replace
# that installer, retaining the upstream metamodule and runtime scripts.
cat > "$module_dir/customize.sh" <<'INSTALL'
ui_print "- NoMount for Cogan (built-in kernel driver)"
[ "$KSU" = true ] || abort "! Install through the matching BakaSU manager."
[ -f "$MODPATH/bin/nm-$ARCH" ] || abort "! Unsupported architecture: $ARCH"
mv "$MODPATH/bin/nm-$ARCH" "$MODPATH/bin/nm"
set_perm "$MODPATH/bin/nm" 0 0 0755
if grep -q '^nomount ' /proc/modules; then
  abort "! A NoMount LKM is active. Boot the matching built-in Cogan kernel first."
fi
"$MODPATH/bin/nm" version >/dev/null 2>&1 ||
  abort "! NoMount API unavailable. Flash the kernel from this bundle and reboot first."
rm -f "$MODPATH"/bin/nm-*
mkdir -p /data/adb/ksu/bin /data/adb/nomount
ln -sf /data/adb/modules/nomount/bin/nm /data/adb/ksu/bin/nm ||
  abort "! Could not create the NoMount userspace link."
rm -f /data/adb/nomount/.booting
ui_print "- Built-in NoMount API detected. Reboot after installation."
INSTALL
archive="$destination/$prefix-NoMount-${expected_commit:0:12}.zip"
(cd "$module_dir" && zip -qr "$archive" .)
unzip -tq "$archive"
printf 'NOMOUNT_MODULE=%s\n' "$archive" >> "$GITHUB_ENV"
