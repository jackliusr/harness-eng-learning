from dataclasses import dataclass

@dataclass
class FakeFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction
    type: str = "function"


@dataclass
class FakeMessage:
    content: str | None = None
    tool_calls: list[FakeToolCall] | None = None


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class FakeResponse:
    message: FakeMessage
    usage: FakeUsage | None = None

    @property
    def choices(self) -> list[FakeChoice]:
        return [FakeChoice(self.message)]


class FakeCompletions:
    def __init__(self, responses: list[FakeResponse]):
        self._responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        if not self._responses:
            raise AssertionError("Fake client has no responses left.")
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeResponse]):
        self.chat = type("FakeChat", (), {})()
        self.chat.completions = FakeCompletions(responses)
        self.base_url = "fake://local"


def fake_text_response(content: str) -> FakeResponse:
    return FakeResponse(
        FakeMessage(content=content),
        FakeUsage(10, len(content) // 4),
    )


def fake_tool_response(name: str, args: dict) -> FakeResponse:
    return FakeResponse(
        FakeMessage(
            tool_calls=[
                FakeToolCall(
                    id="call_1",
                    function=FakeFunction(name, json.dumps(args)),
                )
            ]
        ),
        FakeUsage(10, 5),
    )
