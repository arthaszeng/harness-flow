"""config.py 单元测试"""

from pathlib import Path

from harness.core.config import (
    HarnessConfig,
    ModelsConfig,
    RoleModelConfig,
    resolve_model,
    resolve_role_temperature,
    _deep_merge,
)


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


# ── role_configs tests ───────────────────────────────────────


def test_resolve_model_role_configs_override():
    """role_configs.model 在无 role_overrides 时生效。"""
    models = ModelsConfig(
        default="gpt-4o",
        role_configs={"builder": RoleModelConfig(model="claude-sonnet-4-20250514")},
    )
    assert resolve_model("builder", "cursor", models) == "claude-sonnet-4-20250514"
    assert resolve_model("evaluator", "cursor", models) == "gpt-4o"


def test_resolve_model_role_overrides_wins_over_role_configs():
    """role_overrides 优先于 role_configs。"""
    models = ModelsConfig(
        default="gpt-4o",
        role_overrides={"planner": "o3-pro"},
        role_configs={"planner": RoleModelConfig(model="o3")},
    )
    assert resolve_model("planner", "codex", models) == "o3-pro"


def test_resolve_model_role_configs_wins_over_driver_defaults():
    """role_configs.model 优先于 driver_defaults。"""
    models = ModelsConfig(
        default="gpt-4o",
        driver_defaults={"codex": "o3"},
        role_configs={"evaluator": RoleModelConfig(model="claude-sonnet-4-20250514")},
    )
    assert resolve_model("evaluator", "codex", models) == "claude-sonnet-4-20250514"


def test_resolve_model_role_configs_none_model_falls_through():
    """role_configs 中 model=None 不阻断 fallback。"""
    models = ModelsConfig(
        default="gpt-4o",
        driver_defaults={"codex": "o3"},
        role_configs={"evaluator": RoleModelConfig(temperature=0.3)},
    )
    assert resolve_model("evaluator", "codex", models) == "o3"


def test_resolve_role_temperature():
    models = ModelsConfig(
        default="gpt-4o",
        role_configs={
            "planner": RoleModelConfig(model="o3", temperature=0.2),
            "builder": RoleModelConfig(model="claude-sonnet-4-20250514"),
        },
    )
    assert resolve_role_temperature("planner", models) == 0.2
    assert resolve_role_temperature("builder", models) is None
    assert resolve_role_temperature("evaluator", models) is None


def test_resolve_model_empty_role_configs():
    """role_configs 为空时，行为与之前完全一致。"""
    models = ModelsConfig(default="gpt-4o")
    assert resolve_model("builder", "cursor", models) == "gpt-4o"


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
