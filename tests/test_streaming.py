import asyncio
import threading

from main import _stream_events


def test_stream_bridge_forwards_events_and_releases_semaphore():
    def body():
        yield "one\n"
        yield "two\n"

    async def consume():
        semaphore = asyncio.Semaphore(1)
        cancel_event = threading.Event()
        items = []

        async for item in _stream_events(body(), cancel_event, semaphore):
            items.append(item)

        return items, semaphore.locked(), cancel_event.is_set()

    items, locked, cancelled = asyncio.run(consume())

    assert items == ["one\n", "two\n"]
    assert not locked
    assert not cancelled


def test_stream_bridge_signals_cancel_on_abort():
    def body():
        for index in range(1000):
            yield f"{index}\n"

    async def consume_one():
        semaphore = asyncio.Semaphore(1)
        cancel_event = threading.Event()
        stream = _stream_events(body(), cancel_event, semaphore)

        first = await stream.__anext__()
        await stream.aclose()

        return first, semaphore.locked(), cancel_event.is_set()

    first, locked, cancelled = asyncio.run(consume_one())

    assert first == "0\n"
    assert not locked
    assert cancelled
