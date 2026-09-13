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
    assert "dnf install -y clang libcxx-devel libcxx-static libcxxabi-static" in workflow
    assert "CIBW_MANYLINUX_X86_64_IMAGE: quay.io/pypa/manylinux_2_34_x86_64" in workflow
    assert "CIBW_MANYLINUX_AARCH64_IMAGE: quay.io/pypa/manylinux_2_34_aarch64" in workflow
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
    assert '"${FILAMENT_ROOT}/lib/universal"' in cmake
    assert '"${FILAMENT_ROOT}/lib/aarch64"' in cmake
