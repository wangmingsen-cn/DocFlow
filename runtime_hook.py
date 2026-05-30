"""
PyInstaller runtime hook — patch importlib.metadata to handle
missing package metadata for imageio (and imageio_ffmpeg) in frozen builds.
"""
import importlib.metadata as _imd


# ── Fallback versions for packages whose metadata is missing ──
_FALLBACK_VERSIONS = {
    'imageio': '2.37.3',
    'imageio_ffmpeg': '0.6.0',
}

# ── Save original functions ──
_orig_version = _imd.version
_orig_distribution = _imd.distribution
_orig_metadata = _imd.metadata


def _patched_version(package_name):
    try:
        return _orig_version(package_name)
    except _imd.PackageNotFoundError:
        if package_name in _FALLBACK_VERSIONS:
            return _FALLBACK_VERSIONS[package_name]
        raise


def _patched_distribution(package_name):
    try:
        return _orig_distribution(package_name)
    except _imd.PackageNotFoundError:
        if package_name in _FALLBACK_VERSIONS:
            raise  # Let version() handle the fallback
        raise


def _patched_metadata(package_name):
    try:
        return _orig_metadata(package_name)
    except _imd.PackageNotFoundError:
        if package_name in _FALLBACK_VERSIONS:
            return {
                'Name': package_name,
                'Version': _FALLBACK_VERSIONS[package_name],
            }
        raise


# ── Apply the patches ──
_imd.version = _patched_version
_imd.distribution = _patched_distribution
_imd.metadata = _patched_metadata
