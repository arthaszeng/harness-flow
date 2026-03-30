"""config.py 单元测试"""

from pathlib import Path

from harness.core.config import HarnessConfig, _deep_merge


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
