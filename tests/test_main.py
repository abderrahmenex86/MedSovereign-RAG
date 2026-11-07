from dataclasses import replace

import torch

import main
from src.config import Config


class _FakeOllama:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.model_name = kwargs["model_name"]
        self.backend = "ollama"
        self.checked = False

    def check_ready(self):
        self.checked = True


class _FakeClinical:
    def __init__(self, model_name, device, dtype_preference="auto"):
        self.model_name = model_name
        self.device = device
        self.dtype_preference = dtype_preference
        self.backend = "transformers"


def test_build_generator_selects_ollama(monkeypatch):
    monkeypatch.setattr(main, "OllamaGenerator", _FakeOllama)
    config = replace(Config.from_env(), generator_backend="ollama")

    generator = main._build_generator(config, torch.device("cpu"))

    assert generator.backend == "ollama"
    assert generator.checked is True
    assert generator.kwargs["model_name"] == config.ollama_model
    assert generator.kwargs["keep_alive"] == config.ollama_keep_alive


def test_build_generator_defaults_to_transformers(monkeypatch):
    monkeypatch.setattr(main, "ClinicalGenerator", _FakeClinical)
    config = replace(Config.from_env(), generator_backend="transformers")

    generator = main._build_generator(config, torch.device("cpu"))

    assert generator.backend == "transformers"
    assert generator.model_name == config.generator_model
    assert generator.device.type == "cpu"
