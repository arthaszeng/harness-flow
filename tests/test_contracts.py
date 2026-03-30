"""contracts.py 单元测试"""

from harness.methodology.contracts import parse_contract, verify_deliverables

_SAMPLE = """\
# Contract — Iteration 2

## 交付物
- [ ] 实现用户注册 API
- [x] 添加输入验证
- [ ] 编写单元测试

## 验收标准
1. POST /api/register 返回 201
2. 重复邮箱返回 409
3. 测试覆盖率 > 80%

## 技术摘要
使用 FastAPI + Pydantic 实现。

## 复杂度
medium
"""


def test_parse_contract():
    c = parse_contract(_SAMPLE)
    assert c.iteration == 2
    assert len(c.deliverables) == 3
    assert c.deliverables[1].done is True
    assert c.deliverables[0].done is False
    assert len(c.acceptance_criteria) == 3
    assert c.complexity == "medium"
    assert "FastAPI" in c.technical_summary


def test_verify_deliverables():
    c = parse_contract(_SAMPLE)
    done, total = verify_deliverables(c)
    assert done == 1
    assert total == 3
