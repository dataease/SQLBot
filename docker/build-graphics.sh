#!/bin/sh
set -eu

export DEB_BUILD_OPTIONS='nocheck nodoc parallel=3'
mkdir -p /out /tmp/graphics/harfbuzz /tmp/graphics/pixbuf

add_harfbuzz_patch() {
    patch_path="debian/patches/$1.patch"
    curl -fsSL --retry 3 -o "$patch_path" \
        "https://github.com/harfbuzz/harfbuzz/commit/$2.patch"
    echo "$3  $patch_path" | sha256sum -c -
    printf '\n%s.patch\n' "$1" >> debian/patches/series
}

cd /tmp/graphics/harfbuzz
apt-get source --only-source 'harfbuzz=6.0.0+dfsg-3'
cd harfbuzz-*/
# The fix depends on the matching API introduced by the first commit.
add_harfbuzz_patch sqlbot-skipping-iterator b29fbd16fa82b82bdf0dcb2f13a63f7dc23cf324 \
    480d72df65f946a38f952a85821ded3b312056e3d5c1c51ce84ecd1bf248b59e
add_harfbuzz_patch sqlbot-CVE-2023-25193 8708b9e081192786c027bb7f5f23d76dbe5c19e8 \
    06eb34c2b0c7d546f1ff62fe09e5df1a6d45a28428d05fe532a8f1f28a4590dd
sed -i '1s/) /+sqlbot1) /' debian/changelog
dpkg-buildpackage -b -us -uc
cp ../libharfbuzz0b_*_"$(dpkg --print-architecture)".deb /out/

cd /tmp/graphics/pixbuf
apt-get source --only-source gdk-pixbuf
cd gdk-pixbuf-*/
grep -q -- '-Dauto_features=enabled$' debian/rules
sed -i 's/-Dauto_features=enabled$/-Dauto_features=enabled -Dtiff=disabled \\/' debian/rules
sed -i '1s/) /+sqlbot1) /' debian/changelog
dpkg-buildpackage -b -us -uc
cp ../libgdk-pixbuf-2.0-0_*_"$(dpkg --print-architecture)".deb ../libgdk-pixbuf2.0-common_*_all.deb /out/
