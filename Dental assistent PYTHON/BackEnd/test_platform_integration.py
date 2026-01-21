"""
Integration test for platform-specific code refactoring.
Tests that the platform module works correctly across all operating systems.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.platform import (
    get_platform,
    reset_platform,
    WindowsPlatform,
    MacOSPlatform,
    LinuxPlatform,
    PlatformBase,
)
from app.config import (
    user_data_dir,
    get_hardware_info,
    analyze_hardware,
    HardwareDetector,
)


def test_platform_detection():
    """Test that platform detection works."""
    print("Testing platform detection...")

    platform = get_platform()
    assert isinstance(platform, PlatformBase)
    assert platform.get_platform_name() in ["Windows", "macOS", "Linux"]

    print(f"  ✓ Platform detected: {platform.get_platform_name()}")


def test_all_platform_implementations():
    """Test that all platform implementations work independently."""
    print("\nTesting all platform implementations...")

    platforms = [
        (WindowsPlatform(), "Windows"),
        (MacOSPlatform(), "macOS"),
        (LinuxPlatform(), "Linux"),
    ]

    for platform, expected_name in platforms:
        # Test platform name
        assert platform.get_platform_name() == expected_name
        print(f"  ✓ {expected_name} platform name correct")

        # Test user data directory
        user_dir = platform.get_user_data_dir()
        assert isinstance(user_dir, Path)
        assert len(str(user_dir)) > 0
        print(f"    User dir: {user_dir}")

        # Test GPU detection (may return None, that's ok)
        gpu_info = platform.detect_gpu()
        if gpu_info:
            assert "gpu_name" in gpu_info
            assert "vram_gb" in gpu_info
            assert "detection_method" in gpu_info
            print(f"    GPU detected: {gpu_info['gpu_name']}")
        else:
            print(f"    No GPU detected (expected in CI/test environments)")

        # Test backend GPU support check
        backend_support = platform.check_gpu_backend_support()
        assert isinstance(backend_support, bool)
        print(f"    Backend GPU support: {backend_support}")


def test_user_data_dir_paths():
    """Test that user data directories follow OS conventions."""
    print("\nTesting user data directory paths...")

    windows = WindowsPlatform()
    macos = MacOSPlatform()
    linux = LinuxPlatform()

    # Windows should use AppData
    win_dir = windows.get_user_data_dir("TestApp")
    assert "AppData" in str(win_dir) or "Roaming" in str(win_dir)
    print(f"  ✓ Windows path: {win_dir}")

    # macOS should use Library/Application Support
    mac_dir = macos.get_user_data_dir("TestApp")
    assert "Library" in str(mac_dir) and "Application Support" in str(mac_dir)
    print(f"  ✓ macOS path: {mac_dir}")

    # Linux should use .local/share or XDG_DATA_HOME
    linux_dir = linux.get_user_data_dir("TestApp")
    assert ".local" in str(linux_dir) or "share" in str(linux_dir) or "XDG" in str(linux_dir)
    print(f"  ✓ Linux path: {linux_dir}")


def test_hardware_detector_integration():
    """Test that HardwareDetector uses platform module correctly."""
    print("\nTesting HardwareDetector integration...")

    # Clear cache to force fresh detection
    HardwareDetector._cached_result = None

    hw_info = get_hardware_info()

    # Verify structure
    assert "profile" in hw_info
    assert hw_info["profile"] in ["high_vram", "low_vram", "cpu_only"]
    assert "gpu_detected" in hw_info
    assert "backend_gpu_support" in hw_info
    assert "detection_method" in hw_info

    print(f"  ✓ Hardware profile: {hw_info['profile']}")
    print(f"  ✓ GPU detected: {hw_info['gpu_detected']}")
    print(f"  ✓ Backend support: {hw_info['backend_gpu_support']}")
    print(f"  ✓ Detection method: {hw_info['detection_method']}")

    # Test that analyze_hardware returns a valid profile
    profile = analyze_hardware()
    assert profile in ["high_vram", "low_vram", "cpu_only"]
    print(f"  ✓ Analyzed profile: {profile}")


def test_config_uses_platform():
    """Test that config.py correctly uses platform abstraction."""
    print("\nTesting config.py uses platform abstraction...")

    # Reset platform singleton
    reset_platform()

    # Get user data dir (should use platform module)
    user_dir = user_data_dir("TestApp")
    assert isinstance(user_dir, Path)
    print(f"  ✓ user_data_dir() works: {user_dir}")

    # Get hardware info (should use platform module)
    hw_info = get_hardware_info()
    assert "profile" in hw_info
    print(f"  ✓ get_hardware_info() works: profile={hw_info['profile']}")


def test_platform_singleton():
    """Test that platform uses singleton pattern."""
    print("\nTesting platform singleton pattern...")

    platform1 = get_platform()
    platform2 = get_platform()

    # Should be the same instance
    assert platform1 is platform2
    print(f"  ✓ Singleton pattern works: same instance returned")

    # Reset and get new instance
    reset_platform()
    platform3 = get_platform()

    # Should be different instance after reset
    assert platform1 is not platform3
    print(f"  ✓ Reset works: new instance after reset")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Platform Integration Tests")
    print("=" * 70)

    try:
        test_platform_detection()
        test_all_platform_implementations()
        test_user_data_dir_paths()
        test_hardware_detector_integration()
        test_config_uses_platform()
        test_platform_singleton()

        print("\n" + "=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
