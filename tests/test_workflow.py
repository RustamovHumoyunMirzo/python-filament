from pathlib import Path


def test_workflow_uses_supported_runners_and_node24_actions():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "macos-13" not in workflow
    assert "macos-15-intel" not in workflow
    assert "runner: macos-15," in workflow
    assert "runner: ubuntu-22.04" in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/upload-artifact@v6" in workflow
    assert "actions/download-artifact@v7" in workflow
    assert "softprops/action-gh-release@v3" in workflow
    assert "manylinux-install-clang" not in workflow
    assert "CIBW_BEFORE_ALL_LINUX: sh ci/install_linux_libcxx.sh" in workflow
    assert "dnf install" not in workflow
    assert "LDFLAGS=-L/opt/python-filament-libcxx/lib" in workflow
    assert "LD_LIBRARY_PATH=/opt/python-filament-libcxx/lib" in workflow
    assert "CIBW_REPAIR_WHEEL_COMMAND_LINUX:" in workflow
    image_tag = "2025.04.19-1"
    assert f"quay.io/pypa/manylinux_2_34_x86_64:{image_tag}" in workflow
    assert f"quay.io/pypa/manylinux_2_34_aarch64:{image_tag}" in workflow
    assert "CMAKE_ARGS=-DCMAKE_OSX_ARCHITECTURES=${{ matrix.arch }}" in workflow
    assert "e=filament.Engine()" not in workflow


def test_cibuildwheel_uses_portable_sdk_archive_path():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    cmake = Path("CMakeLists.txt").read_text(encoding="utf-8")
    assert "FILAMENT_ARCHIVE=filament-sdk.tgz" in workflow
    assert "${{ github.workspace }}/filament-sdk.tgz" not in workflow
    assert 'BASE_DIR "${CMAKE_SOURCE_DIR}"' in cmake
    assert 'if(NOT EXISTS "${FILAMENT_ARCHIVE}")' in cmake
    assert "if: matrix.sdk != ''" in workflow
    assert '"${_filament_extract_dir}/filament/include/filament/Engine.h"' in cmake
    assert "if(APPLE AND CMAKE_OSX_ARCHITECTURES)" in cmake
    assert 'if(_filament_arch MATCHES "^(AMD64|amd64|x86_64)$")' in cmake
    assert "target_link_libraries(_native PRIVATE c++ c++abi dl pthread)" in cmake
    assert '"${FILAMENT_ROOT}/lib/universal"' in cmake
    assert '"${FILAMENT_ROOT}/lib/aarch64"' in cmake


def test_linux_libcxx_bootstrap_is_pinned_for_both_architectures():
    script = Path("ci/install_linux_libcxx.sh").read_text(encoding="utf-8")
    assert "version=8.0.0" in script
    assert "subdir=linux-64" in script
    assert "subdir=linux-aarch64" in script
    assert script.count("md5sum -c -") == 2
    assert "curl -fL --retry 3" in script
    assert "dnf install" not in script
