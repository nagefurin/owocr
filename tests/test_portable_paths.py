import os
import sys

from owocr import paths


def configure_packaged_paths(monkeypatch, executable_dir, user_config_dir):
    executable_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(executable_dir / "owocr.exe"))
    monkeypatch.setattr(paths, "USER_CONFIG_DIR", user_config_dir)
    return executable_dir / ".config"


def test_fresh_packaged_install_uses_portable_config(monkeypatch, tmp_path):
    portable_dir = configure_packaged_paths(
        monkeypatch, tmp_path / "owocr", tmp_path / "user-config"
    )

    assert paths.get_config_dir() == portable_dir
    assert paths.get_config_path("owocr_config.ini") == portable_dir / "owocr_config.ini"


def test_empty_portable_config_falls_back_to_existing_user_config(monkeypatch, tmp_path):
    user_config = tmp_path / "user-config"
    user_config.mkdir()
    (user_config / "owocr_config.ini").write_text("[general]\n", encoding="utf-8")
    portable_dir = configure_packaged_paths(monkeypatch, tmp_path / "owocr", user_config)
    portable_dir.mkdir()

    assert paths.get_config_dir() == user_config
    assert not paths.is_portable_mode()


def test_populated_portable_config_takes_priority(monkeypatch, tmp_path):
    user_config = tmp_path / "user-config"
    user_config.mkdir()
    (user_config / "owocr_config.ini").write_text("[general]\n", encoding="utf-8")
    portable_dir = configure_packaged_paths(monkeypatch, tmp_path / "owocr", user_config)
    portable_dir.mkdir()
    (portable_dir / "owocr_config.ini").write_text("[general]\n", encoding="utf-8")

    assert paths.get_config_dir() == portable_dir
    assert paths.is_portable_mode()


def test_portable_mode_redirects_model_caches(monkeypatch, tmp_path):
    portable_dir = configure_packaged_paths(
        monkeypatch, tmp_path / "owocr", tmp_path / "user-config"
    )
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HF_HUB_CACHE", raising=False)
    monkeypatch.delenv("TORCH_HOME", raising=False)
    monkeypatch.delenv("EASYOCR_MODULE_PATH", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    paths.configure_portable_caches()

    assert os.environ["HF_HOME"] == str(portable_dir / "huggingface")
    assert os.environ["HF_HUB_CACHE"] == str(portable_dir / "huggingface" / "hub")
    assert os.environ["TORCH_HOME"] == str(portable_dir / "torch")
    assert os.environ["EASYOCR_MODULE_PATH"] == str(portable_dir / "easyocr")
    assert os.environ["XDG_CACHE_HOME"] == str(portable_dir / "cache")


def test_python_install_uses_user_config(monkeypatch, tmp_path):
    user_config = tmp_path / "user-config"
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    monkeypatch.setattr(paths, "USER_CONFIG_DIR", user_config)

    assert paths.get_config_dir() == user_config
    assert not paths.is_portable_mode()
