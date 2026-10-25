"""Path helpers for normal and portable OWOCR installations."""

import os
import re
import sys
from pathlib import Path


USER_CONFIG_DIR = Path.home() / ".config"


def expand_path_variables(value):
    """Expand environment variables in a configured path.

    Support the native environment-variable syntax and Windows-style %NAME%
    references, even when a config file is inspected on a non-Windows host.
    """
    value = os.path.expandvars(os.fspath(value))
    return re.sub(
        r"%([^%]+)%",
        lambda match: os.environ.get(match.group(1), match.group(0)),
        value,
    )


def get_executable_dir():
    """Return the directory containing the frozen executable, or None for Python installs."""
    if not getattr(sys, "frozen", False):
        return None
    try:
        return Path(sys.executable).resolve().parent
    except (OSError, RuntimeError):
        return Path(sys.executable).absolute().parent


def get_portable_config_dir():
    """Return the config directory next to the executable for a packaged build."""
    executable_dir = get_executable_dir()
    return executable_dir / "config" if executable_dir is not None else None


def _has_entries(directory):
    """Whether a directory exists and contains at least one entry."""
    try:
        return directory.is_dir() and next(directory.iterdir(), None) is not None
    except OSError:
        return False


def get_config_dir():
    """Choose portable data when present, otherwise preserve the user's existing config.

    A fresh packaged install starts portable if neither location has data. If the
    executable-side config is empty but the user's .config has content, the user
    directory remains the fallback until the portable directory is populated.
    """
    portable_dir = get_portable_config_dir()
    if portable_dir is None:
        return USER_CONFIG_DIR

    if _has_entries(portable_dir):
        return portable_dir

    if _has_entries(USER_CONFIG_DIR):
        return USER_CONFIG_DIR

    return portable_dir


def is_portable_mode():
    """Return True when a frozen build is using the executable-side config."""
    portable_dir = get_portable_config_dir()
    return portable_dir is not None and get_config_dir() == portable_dir


def get_config_path(filename):
    return get_config_dir() / filename


def get_cache_dir(name):
    """Return a per-engine cache directory without changing source-install defaults."""
    if is_portable_mode():
        return get_config_dir() / "cache" / name
    return Path.home() / ".cache" / name


def configure_portable_caches():
    """Redirect common ML model caches beside the executable in portable mode.

    In portable mode the executable-side cache paths take priority so models do
    not silently spill into a machine-wide or user-profile cache.
    """
    if not is_portable_mode():
        return

    config_dir = get_config_dir()
    huggingface_dir = config_dir / "huggingface"
    cache_values = {
        "HF_HOME": huggingface_dir,
        "HF_HUB_CACHE": huggingface_dir / "hub",
        "HF_ASSETS_CACHE": huggingface_dir / "assets",
        "HUGGINGFACE_HUB_CACHE": huggingface_dir / "hub",
        "TRANSFORMERS_CACHE": huggingface_dir / "transformers",
        "TORCH_HOME": config_dir / "torch",
        "EASYOCR_MODULE_PATH": config_dir / "easyocr",
        "XDG_CACHE_HOME": config_dir / "cache",
    }

    for key, value in cache_values.items():
        os.environ[key] = str(value)
