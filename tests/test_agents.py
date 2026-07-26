"""Agent state tests."""
from agents.base import AgentState, AgentRole, Tool


def test_agent_state_default():
    s = AgentState()
    assert s.task_id is None
    assert s.input == ""
    assert s.context == {}
    assert s.history == []
    assert s.artifacts == {}
    assert s.errors == []
    assert s.done is False


def test_agent_state_serialize():
    s = AgentState(task_id=1, user_id=2, input="build a thing")
    d = s.to_dict()
    assert d["task_id"] == 1
    assert d["user_id"] == 2
    assert d["input"] == "build a thing"


def test_tool_schema():
    def my_func(x: str) -> str:
        return x

    t = Tool(
        name="my_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
        func=my_func,
    )
    schema = t.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "my_tool"
    assert "x" in schema["function"]["parameters"]["properties"]
