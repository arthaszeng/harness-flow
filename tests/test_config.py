"""config.py 单元测试"""

from pathlib import Path

from harness.core.config import HarnessConfig, ModelsConfig, resolve_model, _deep_merge


def test_default_config():
    cfg = HarnessConfig()
    assert cfg.workflow.max_iterations == 3
    assert cfg.workflow.pass_threshold == 3.5
    assert cfg.drivers.default == "auto"
    assert cfg.integrations.memverse.enabled is False


def test_load_from_toml(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test-proj"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    assert cfg.project.name == "test-proj"
    assert cfg.ci.command == "pytest"
    assert cfg.workflow.max_iterations == 3  # 默认值


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}, "e": 5}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}


# ── model resolution tests ──────────────────────────────────────


def test_resolve_model_global_default():
    models = ModelsConfig(default="gpt-4o")
    assert resolve_model("planner", "codex", models) == "gpt-4o"
    assert resolve_model("builder", "cursor", models) == "gpt-4o"


def test_resolve_model_driver_default_overrides_global():
    models = ModelsConfig(
        default="gpt-4o",
        driver_defaults={"codex": "o3"},
    )
    assert resolve_model("evaluator", "codex", models) == "o3"
    assert resolve_model("builder", "cursor", models) == "gpt-4o"


def test_resolve_model_role_override_overrides_all():
    models = ModelsConfig(
        default="gpt-4o",
        driver_defaults={"codex": "o3"},
        role_overrides={"planner": "o3-pro"},
    )
    assert resolve_model("planner", "codex", models) == "o3-pro"
    assert resolve_model("evaluator", "codex", models) == "o3"
    assert resolve_model("builder", "cursor", models) == "gpt-4o"


def test_resolve_model_empty_default():
    models = ModelsConfig(default="")
    assert resolve_model("planner", "codex", models) == ""


def test_models_config_from_toml(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[models]\ndefault = "gpt-4o"\n\n'
        '[models.driver_defaults]\ncodex = "o3"\n\n'
        '[models.role_overrides]\nplanner = "o3-pro"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    assert cfg.models.default == "gpt-4o"
    assert cfg.models.driver_defaults == {"codex": "o3"}
    assert cfg.models.role_overrides == {"planner": "o3-pro"}
