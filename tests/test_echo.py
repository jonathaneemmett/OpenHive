from openhive.server import echo


async def test_echo_returns_message():
    result = await echo(message="hello")
    assert result == "hello"


async def test_echo_empty_string():
    result = await echo(message="")
    assert result == ""
