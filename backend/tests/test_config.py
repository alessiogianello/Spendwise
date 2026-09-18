from app.config import Settings


def test_llm_model_env_var_is_read(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "deepseek/deepseek-v3.2")
    assert Settings(_env_file=None).model == "deepseek/deepseek-v3.2"


def test_model_defaults_without_env(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert Settings(_env_file=None).model == "anthropic/claude-opus-5"
