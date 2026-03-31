"""insights 模块单元测试 — 覆盖正常、带 alignment、无 alignment、降级场景。"""

from __future__ import annotations

import json
from pathlib import Path

from harness.methodology.insights import (
    _extract_alignment_flags,
    _extract_learning,
    generate_task_insights,
    load_task_insights,
    write_task_insights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_eval_sidecar(task_dir: Path, iteration: int = 1, **overrides) -> Path:
    """写入一个 evaluation JSON sidecar 到 task_dir。"""
    data = {
        "iteration": iteration,
        "scores": {
            "completeness": 4.0,
            "quality": 4.5,
            "regression": 3.8,
            "design": 4.2,
        },
        "weighted": 4.08,
        "verdict": "PASS",
        "feedback": ["looks good", "tests pass"],
    }
    data.update(overrides)
    path = task_dir / f"evaluation-r{iteration}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _write_eval_md(task_dir: Path, iteration: int = 1) -> Path:
    path = task_dir / f"evaluation-r{iteration}.md"
    path.write_text("# Evaluation\nPASS", encoding="utf-8")
    return path


def _write_alignment_md(
    task_dir: Path, iteration: int = 1, content: str = "ALIGNED",
) -> Path:
    path = task_dir / f"alignment-r{iteration}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# _extract_alignment_flags
# ---------------------------------------------------------------------------

class TestExtractAlignmentFlags:
    def test_aligned(self):
        result = _extract_alignment_flags("Everything looks ALIGNED with the contract.")
        assert result.has_alignment is True
        assert result.aligned is True
        assert result.misaligned is False
        assert result.contract_issue is False

    def test_misaligned(self):
        result = _extract_alignment_flags("Verdict: MISALIGNED — missing deliverable 2.")
        assert result.has_alignment is True
        assert result.aligned is False
        assert result.misaligned is True

    def test_contract_issue(self):
        result = _extract_alignment_flags("Found CONTRACT_ISSUE in acceptance criteria.")
        assert result.has_alignment is True
        assert result.aligned is False
        assert result.contract_issue is True

    def test_misaligned_takes_priority_over_contract_issue(self):
        result = _extract_alignment_flags("MISALIGNED and also CONTRACT_ISSUE")
        assert result.misaligned is True
        assert result.contract_issue is False


# ---------------------------------------------------------------------------
# _extract_learning
# ---------------------------------------------------------------------------

class TestExtractLearning:
    def test_strong_scores_become_strengths(self):
        data = {"scores": {"completeness": 4.5, "quality": 4.0, "regression": 2.5, "design": 3.5}}
        result = _extract_learning(data)
        assert len(result.strengths) == 2
        assert any("completeness" in s for s in result.strengths)
        assert any("quality" in s for s in result.strengths)

    def test_weak_scores_become_issues(self):
        data = {"scores": {"completeness": 2.0, "quality": 1.5, "regression": 4.0, "design": 4.0}}
        result = _extract_learning(data)
        assert len(result.issues) == 2
        assert any("completeness" in s for s in result.issues)
        assert len(result.next_focus) == 2

    def test_empty_scores(self):
        result = _extract_learning({"scores": {}})
        assert result.strengths == []
        assert result.issues == []

    def test_missing_scores_key(self):
        result = _extract_learning({})
        assert result.strengths == []


# ---------------------------------------------------------------------------
# generate_task_insights — PASS 场景
# ---------------------------------------------------------------------------

class TestGenerateInsightsPass:
    def test_with_eval_sidecar(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        _write_eval_md(tmp_path)

        insights = generate_task_insights(
            task_id="task-001",
            requirement="add feature X",
            verdict="PASS",
            iterations=1,
            task_dir=tmp_path,
        )

        assert insights.schema_version == "1.0"
        assert insights.task.verdict == "PASS"
        assert insights.quality_summary is not None
        assert insights.quality_summary.weighted_score > 0
        assert insights.quality_summary.evaluation_verdict == "PASS"
        assert insights.source_artifacts.evaluation_json == "evaluation-r1.json"
        assert insights.source_artifacts.evaluation_md == "evaluation-r1.md"
        assert insights.alignment_summary.has_alignment is False

    def test_with_alignment_aligned(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        _write_eval_md(tmp_path)
        _write_alignment_md(tmp_path, content="Everything is ALIGNED.")

        insights = generate_task_insights(
            task_id="task-002",
            requirement="add feature Y",
            verdict="PASS",
            iterations=2,
            task_dir=tmp_path,
        )

        assert insights.alignment_summary.has_alignment is True
        assert insights.alignment_summary.aligned is True
        assert insights.source_artifacts.alignment_md == "alignment-r1.md"

    def test_with_alignment_misaligned(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        _write_eval_md(tmp_path)
        _write_alignment_md(tmp_path, content="MISALIGNED: missing deliverable.")

        insights = generate_task_insights(
            task_id="task-003",
            requirement="refactor Z",
            verdict="PASS",
            iterations=1,
            task_dir=tmp_path,
        )

        assert insights.alignment_summary.has_alignment is True
        assert insights.alignment_summary.misaligned is True
        assert insights.alignment_summary.aligned is False

    def test_with_alignment_contract_issue(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        _write_eval_md(tmp_path)
        _write_alignment_md(tmp_path, content="CONTRACT_ISSUE detected.")

        insights = generate_task_insights(
            task_id="task-004",
            requirement="fix bug",
            verdict="PASS",
            iterations=1,
            task_dir=tmp_path,
        )

        assert insights.alignment_summary.contract_issue is True
        assert insights.alignment_summary.aligned is False

    def test_picks_latest_iteration(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path, iteration=1, weighted=2.0, verdict="ITERATE")
        _write_eval_md(tmp_path, iteration=1)
        _write_eval_sidecar(tmp_path, iteration=2, weighted=4.5, verdict="PASS")
        _write_eval_md(tmp_path, iteration=2)

        insights = generate_task_insights(
            task_id="task-005",
            requirement="multi-iter task",
            verdict="PASS",
            iterations=2,
            task_dir=tmp_path,
        )

        assert insights.quality_summary is not None
        assert insights.quality_summary.weighted_score == 4.5
        assert insights.source_artifacts.evaluation_json == "evaluation-r2.json"


# ---------------------------------------------------------------------------
# generate_task_insights — BLOCKED 场景
# ---------------------------------------------------------------------------

class TestGenerateInsightsBlocked:
    def test_with_eval_sidecar(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path, verdict="ITERATE", weighted=2.0)
        _write_eval_md(tmp_path)

        insights = generate_task_insights(
            task_id="task-010",
            requirement="hard task",
            verdict="BLOCKED",
            iterations=3,
            task_dir=tmp_path,
            feedback="max iterations reached",
        )

        assert insights.task.verdict == "BLOCKED"
        assert insights.quality_summary is not None
        assert insights.quality_summary.evaluation_verdict == "ITERATE"

    def test_without_eval_sidecar_degraded(self, tmp_path: Path):
        """缺少 evaluation sidecar 时产出降级摘要。"""
        insights = generate_task_insights(
            task_id="task-011",
            requirement="early failure",
            verdict="BLOCKED",
            iterations=1,
            task_dir=tmp_path,
            feedback="planner failed (exit 1)",
        )

        assert insights.task.verdict == "BLOCKED"
        assert insights.quality_summary is None
        assert insights.alignment_summary.has_alignment is False
        assert "planner failed" in insights.learning_summary.issues[0]
        assert insights.source_artifacts.evaluation_json is None

    def test_without_anything(self, tmp_path: Path):
        """完全空目录也不报错。"""
        insights = generate_task_insights(
            task_id="task-012",
            requirement="nothing",
            verdict="BLOCKED",
            iterations=0,
            task_dir=tmp_path,
        )

        assert insights.task.verdict == "BLOCKED"
        assert insights.quality_summary is None
        assert insights.learning_summary.issues == []


# ---------------------------------------------------------------------------
# write / load round-trip
# ---------------------------------------------------------------------------

class TestWriteAndLoad:
    def test_round_trip(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        _write_eval_md(tmp_path)
        _write_alignment_md(tmp_path, content="ALIGNED")

        original = generate_task_insights(
            task_id="task-020",
            requirement="round trip",
            verdict="PASS",
            iterations=1,
            task_dir=tmp_path,
        )
        write_task_insights(original, tmp_path)

        loaded = load_task_insights(tmp_path)
        assert loaded is not None
        assert loaded.schema_version == original.schema_version
        assert loaded.task.task_id == "task-020"
        assert loaded.quality_summary is not None
        assert loaded.quality_summary.weighted_score == original.quality_summary.weighted_score
        assert loaded.alignment_summary.has_alignment is True

    def test_load_missing_file(self, tmp_path: Path):
        assert load_task_insights(tmp_path) is None

    def test_load_corrupt_file(self, tmp_path: Path):
        (tmp_path / "insights.json").write_text("not json", encoding="utf-8")
        assert load_task_insights(tmp_path) is None

    def test_json_contains_schema_version(self, tmp_path: Path):
        _write_eval_sidecar(tmp_path)
        insights = generate_task_insights(
            task_id="task-021",
            requirement="check schema",
            verdict="PASS",
            iterations=1,
            task_dir=tmp_path,
        )
        path = write_task_insights(insights, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "schema_version" in data
        assert "generated_at" in data
        assert data["task"]["task_id"] == "task-021"

    def test_degraded_round_trip(self, tmp_path: Path):
        """降级摘要也能正确序列化/反序列化。"""
        original = generate_task_insights(
            task_id="task-022",
            requirement="degraded",
            verdict="BLOCKED",
            iterations=1,
            task_dir=tmp_path,
            feedback="early abort",
        )
        write_task_insights(original, tmp_path)

        loaded = load_task_insights(tmp_path)
        assert loaded is not None
        assert loaded.quality_summary is None
        assert loaded.task.verdict == "BLOCKED"
