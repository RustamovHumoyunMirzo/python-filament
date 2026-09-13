from pathlib import Path


def test_workflow_uses_supported_runners_and_node24_actions():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "macos-13" not in workflow
    assert "macos-15-intel" in workflow
    assert "runner: macos-15," in workflow
    assert "runner: ubuntu-22.04" in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/upload-artifact@v6" in workflow
    assert "actions/download-artifact@v7" in workflow
    assert "softprops/action-gh-release@v3" in workflow
    assert "manylinux-install-clang -l" in workflow
    assert "e=filament.Engine()" not in workflow


def test_cibuildwheel_uses_portable_sdk_archive_path():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    cmake = Path("CMakeLists.txt").read_text(encoding="utf-8")
    assert "FILAMENT_ARCHIVE=filament-sdk.tgz" in workflow
    assert "${{ github.workspace }}/filament-sdk.tgz" not in workflow
    assert 'BASE_DIR "${CMAKE_SOURCE_DIR}"' in cmake
    assert 'if(NOT EXISTS "${FILAMENT_ARCHIVE}")' in cmake
    assert "if: matrix.sdk != ''" in workflow
    assert '"${FILAMENT_ROOT}/lib/universal"' in cmake
    assert '"${FILAMENT_ROOT}/lib/aarch64"' in cmake
