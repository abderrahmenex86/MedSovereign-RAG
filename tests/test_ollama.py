import json

import httpx
import pytest

from src.models import OllamaGenerator


def _generator(handler, think=None):
    client = httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )
    return OllamaGenerator(
        "medgemma:4b",
        base_url="http://ollama.test",
        num_ctx=4096,
        think=think,
        client=client,
    )


def test_check_ready_accepts_pulled_model():
    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "medgemma:4b"}]})

    _generator(handler).check_ready()


def test_check_ready_explains_missing_model():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]})

    with pytest.raises(RuntimeError, match="ollama pull medgemma:4b"):
        _generator(handler).check_ready()


def test_check_ready_explains_unreachable_server():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(RuntimeError, match="ollama serve"):
        _generator(handler).check_ready()


def test_generate_sends_greedy_options():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "PASS"}})

    result = _generator(handler).generate("system", "user", max_tokens=8)

    assert result == "PASS"
    assert captured["model"] == "medgemma:4b"
    assert captured["stream"] is False
    assert captured["keep_alive"] == "10m"
    assert captured["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert captured["options"]["temperature"] == 0.0
    assert captured["options"]["num_ctx"] == 4096
    assert captured["options"]["num_predict"] == 8
    assert "think" not in captured


def test_generate_forwards_think_flag_when_configured():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "PASS"}})

    _generator(handler, think=False).generate("system", "user")

    assert captured["think"] is False


def test_generate_stream_yields_content_until_done():
    body = b"\n".join(
        [
            json.dumps({"message": {"content": "Acute "}, "done": False}).encode(),
            json.dumps({"message": {"content": ""}, "done": False}).encode(),
            json.dumps({"message": {"content": "bronchitis."}, "done": False}).encode(),
            json.dumps({"message": {"content": ""}, "done": True}).encode(),
        ]
    )

    generator = _generator(lambda request: httpx.Response(200, content=body))

    assert list(generator.generate_stream("system", "user")) == ["Acute ", "bronchitis."]


def test_generate_stream_raises_on_error_chunk():
    body = json.dumps({"error": "model is loading"}).encode() + b"\n"

    generator = _generator(lambda request: httpx.Response(200, content=body))

    with pytest.raises(RuntimeError, match="model is loading"):
        list(generator.generate_stream("system", "user"))


def test_generate_raises_on_http_error():
    def handler(request):
        return httpx.Response(404, json={"error": "model 'x' not found"})

    with pytest.raises(RuntimeError, match="404"):
        _generator(handler).generate("system", "user")
