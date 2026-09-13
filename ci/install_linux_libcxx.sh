#!/bin/sh
set -eu

# AlmaLinux's repositories do not ship libc++ for every manylinux architecture.
# Use the last conda-forge libc++ release available for both x86_64 and aarch64.
version=8.0.0
build=4
case "$(uname -m)" in
  x86_64)
    subdir=linux-64
    libcxx_md5=79a583419390ef7a0b7d4290f114e598
    libcxxabi_md5=53b31fbdaed940fb6f9cf663e10af5d7
    ;;
  aarch64)
    subdir=linux-aarch64
    libcxx_md5=e76a5c271d5c3cfb95f804f3d371ab55
    libcxxabi_md5=2221c9bfeb3a6a9646be626889687311
    ;;
  *)
    echo "Unsupported Linux architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

dnf install -y clang
install_dir=/opt/python-filament-libcxx
download_dir=/tmp/python-filament-libcxx
mkdir -p "$install_dir" "$download_dir"

for package in libcxx libcxxabi; do
  archive="$download_dir/$package.tar.bz2"
  url="https://api.anaconda.org/download/conda-forge/$package/$version/$subdir/$package-$version-$build.tar.bz2"
  curl -fL --retry 3 "$url" -o "$archive"
done

printf '%s  %s\n' "$libcxx_md5" "$download_dir/libcxx.tar.bz2" | md5sum -c -
printf '%s  %s\n' "$libcxxabi_md5" "$download_dir/libcxxabi.tar.bz2" | md5sum -c -
tar -xjf "$download_dir/libcxx.tar.bz2" -C "$install_dir"
tar -xjf "$download_dir/libcxxabi.tar.bz2" -C "$install_dir"

test -e "$install_dir/lib/libc++.so"
test -e "$install_dir/lib/libc++abi.so"
