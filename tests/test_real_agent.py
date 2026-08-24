from services.agent.real_agent import ModelRegistry


def test_model_registry_contains_real_providers():
    registry = ModelRegistry()
    providers = {spec.provider for spec in registry.models}
    assert {"openai", "anthropic", "gemini", "groq", "ollama"} <= providers


def test_model_ids_are_not_empty():
    registry = ModelRegistry()
    assert all(spec.id.strip() for spec in registry.models)


def test_unknown_model_is_rejected():
    registry = ModelRegistry()
    try:
        registry.get("definitely-not-a-real-model")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown model must raise ValueError")
