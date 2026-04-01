"""skill_gen.py 扩展功能测试：角色裁剪、项目语言检测、hook、资源部署"""

from pathlib import Path

from harness.core.config import HarnessConfig
from harness.native.skill_gen import (
    _build_context,
    _detect_project_lang,
    generate_native_artifacts,
)


def test_detect_project_lang_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    assert _detect_project_lang(cfg) == "python"


def test_detect_project_lang_typescript(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    assert _detect_project_lang(cfg) == "typescript"


def test_detect_project_lang_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    assert _detect_project_lang(cfg) == "go"


def test_detect_project_lang_unknown(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    assert _detect_project_lang(cfg) == "unknown"


def test_build_context_default_has_all_keys(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    ctx = _build_context(cfg)
    assert "ci_command" in ctx
    assert "trunk_branch" in ctx
    assert "project_lang" in ctx
    assert "planner_principles" in ctx
    assert "builder_principles" in ctx
    assert "hooks_pre_build" in ctx


def test_build_context_adversarial_strips_keys(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    ctx = _build_context(cfg, role="adversarial_reviewer")
    assert "builder_principles" not in ctx
    assert "planner_principles" not in ctx
    assert "ci_command" not in ctx
    assert "trunk_branch" in ctx
    assert "adversarial_model" in ctx


def test_build_context_evaluator_strips_planner_principles(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    ctx = _build_context(cfg, role="evaluator")
    assert "planner_principles" not in ctx
    assert "ci_command" in ctx
    assert "builder_principles" in ctx


def test_build_context_planner_strips_builder_principles(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    ctx = _build_context(cfg, role="planner")
    assert "builder_principles" not in ctx
    assert "planner_principles" in ctx


def test_build_context_hooks_from_config(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    cfg.native.hooks_pre_build = "scripts/pre.sh"
    cfg.native.hooks_post_eval = "scripts/post.sh"
    ctx = _build_context(cfg)
    assert ctx["hooks_pre_build"] == "scripts/pre.sh"
    assert ctx["hooks_post_eval"] == "scripts/post.sh"


def test_build_context_has_review_gate(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    ctx = _build_context(cfg)
    assert "review_gate" in ctx
    assert ctx["review_gate"] == "eng"


def test_build_context_review_gate_custom(tmp_path: Path):
    cfg = HarnessConfig()
    cfg.project_root = tmp_path
    cfg.native.review_gate = "advisory"
    ctx = _build_context(cfg)
    assert ctx["review_gate"] == "advisory"


def test_generate_deploys_resource_files(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "make test"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    count = generate_native_artifacts(tmp_path, cfg=cfg)
    assert count >= 19

    eval_dir = tmp_path / ".cursor" / "skills" / "harness" / "harness-eval"
    assert (eval_dir / "review-checklist.md").exists()
    assert (eval_dir / "specialists" / "testing.md").exists()
    assert (eval_dir / "specialists" / "security.md").exists()
    assert (eval_dir / "specialists" / "performance.md").exists()
    assert (eval_dir / "specialists" / "red-team.md").exists()


def test_generated_skill_contains_project_lang_section(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    cfg = HarnessConfig.load(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)

    build_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-build" / "SKILL.md")
    content = build_skill.read_text(encoding="utf-8")
    assert "Python-Specific Guidance" in content
    assert "ruff check" in content


def test_generated_skill_includes_error_recovery(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)

    build_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-build" / "SKILL.md")
    content = build_skill.read_text(encoding="utf-8")
    assert "Error Recovery Matrix" in content
    assert "Import error" in content


def test_generated_eval_includes_trust_boundary(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)

    eval_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-eval" / "SKILL.md")
    content = eval_skill.read_text(encoding="utf-8")
    assert "Trust Boundaries" in content
    assert "UNTRUSTED" in content


def test_generated_ship_includes_bypass_immunity(tmp_path: Path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    cfg = HarnessConfig.load(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)

    ship_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-ship" / "SKILL.md")
    content = ship_skill.read_text(encoding="utf-8")
    assert "Bypass-Immune" in content
    assert "Safety Rules" in content


def test_fix_first_llm_output_is_ask():
    """fix-first template classifies LLM→DB as ASK (not AUTO-FIX)."""
    from harness.native.skill_gen import _get_template_dir, _render_template

    tmpl_dir = _get_template_dir()
    ctx = {"ci_command": "pytest", "trunk_branch": "main"}
    content = _render_template(tmpl_dir, "rule-fix-first.mdc.j2", ctx)
    assert "LLM output written to DB without validation | ASK" in content


def _make_cfg(tmp_path: Path) -> HarnessConfig:
    """Helper: create a minimal config for generation tests."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "config.toml").write_text(
        '[project]\nname = "test"\n[ci]\ncommand = "pytest"\n',
        encoding="utf-8",
    )
    return HarnessConfig.load(tmp_path)


def test_generated_ship_includes_ci_verification(tmp_path: Path):
    """ship template now includes _ci-verification section partial."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    ship = (tmp_path / ".cursor" / "skills" / "harness" / "harness-ship" / "SKILL.md")
    content = ship.read_text(encoding="utf-8")
    assert "CI Verification" in content


def test_generated_eval_includes_hook_points_when_configured(tmp_path: Path):
    """eval template includes hook section when hooks_post_eval is set."""
    cfg = _make_cfg(tmp_path)
    cfg.native.hooks_post_eval = "scripts/post-eval.sh"
    generate_native_artifacts(tmp_path, cfg=cfg)
    eval_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-eval" / "SKILL.md")
    content = eval_skill.read_text(encoding="utf-8")
    assert "Post-Eval Hook" in content
    assert "scripts/post-eval.sh" in content


def test_generated_eval_no_hook_residue_when_empty(tmp_path: Path):
    """eval template omits hook section when no hooks configured."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    eval_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-eval" / "SKILL.md")
    content = eval_skill.read_text(encoding="utf-8")
    assert "Post-Eval Hook" not in content


def test_generated_eval_has_rust_lang_review(tmp_path: Path):
    """eval template includes Rust review focus for Rust projects."""
    cfg = _make_cfg(tmp_path)
    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    cfg = HarnessConfig.load(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    eval_skill = (tmp_path / ".cursor" / "skills" / "harness" / "harness-eval" / "SKILL.md")
    content = eval_skill.read_text(encoding="utf-8")
    assert "Rust-Specific Review Focus" in content
    assert "unwrap()" in content


def test_generated_ship_advisory_mode(tmp_path: Path):
    """ship Step 6 uses advisory wording when review_gate=advisory."""
    cfg = _make_cfg(tmp_path)
    cfg.native.review_gate = "advisory"
    generate_native_artifacts(tmp_path, cfg=cfg)
    ship = (tmp_path / ".cursor" / "skills" / "harness" / "harness-ship" / "SKILL.md")
    content = ship.read_text(encoding="utf-8")
    assert "advisory mode" in content
    assert "does not block" in content


def test_generated_evaluator_has_output_contract(tmp_path: Path):
    """agent-evaluator uses _output-format-eval section partial."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    evaluator = (tmp_path / ".cursor" / "agents" / "harness-evaluator.md")
    content = evaluator.read_text(encoding="utf-8")
    assert "Output Contract" in content
    assert "VALIDATION RULES" in content


def test_generated_build_no_hook_residue_when_empty(tmp_path: Path):
    """build template has clean formatting when no hooks are set."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    build = (tmp_path / ".cursor" / "skills" / "harness" / "harness-build" / "SKILL.md")
    content = build.read_text(encoding="utf-8")
    assert "Pre-Build Hook" not in content
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "## Step 6: Commit":
            prev_non_empty = ""
            for j in range(i - 1, -1, -1):
                if lines[j].strip():
                    prev_non_empty = lines[j].strip()
                    break
            assert prev_non_empty != "---", "Orphan --- before Step 6 when hooks empty"
            break


def test_review_checklist_uses_main_not_origin(tmp_path: Path):
    """review-checklist uses main..HEAD, not origin/main."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    checklist = (tmp_path / ".cursor" / "skills" / "harness" / "harness-eval" / "review-checklist.md")
    content = checklist.read_text(encoding="utf-8")
    assert "git diff main..HEAD" in content
    assert "origin/main" not in content


def test_retro_uses_real_template_path(tmp_path: Path):
    """retro template references actual file path, not fictional one."""
    cfg = _make_cfg(tmp_path)
    generate_native_artifacts(tmp_path, cfg=cfg)
    retro = (tmp_path / ".cursor" / "skills" / "harness" / "harness-retro" / "SKILL.md")
    content = retro.read_text(encoding="utf-8")
    assert "src/harness/templates/ship.j2" not in content
    assert "skill-ship.md.j2" in content
