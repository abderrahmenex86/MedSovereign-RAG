import pytest

from src.config import Config


def test_defaults_to_transformers(monkeypatch):
    monkeypatch.delenv("GENERATOR_BACKEND", raising=False)

    assert Config.from_env().generator_backend == "transformers"


def test_ollama_backend_settings(monkeypatch):
    monkeypatch.setenv("GENERATOR_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "medgemma:4b")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")

    config = Config.from_env()

    assert config.generator_backend == "ollama"
    assert config.ollama_model == "medgemma:4b"
    assert config.ollama_num_ctx == 4096


def test_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("GENERATOR_BACKEND", "vllm")

    with pytest.raises(ValueError, match="GENERATOR_BACKEND"):
        Config.from_env()


def test_think_is_optional(monkeypatch):
    monkeypatch.delenv("OLLAMA_THINK", raising=False)
    assert Config.from_env().ollama_think is None

    monkeypatch.setenv("OLLAMA_THINK", "false")
    assert Config.from_env().ollama_think is False

    with pytest.raises(ValueError, match="OLLAMA_THINK"):
        monkeypatch.setenv("OLLAMA_THINK", "sometimes")
        Config.from_env()
