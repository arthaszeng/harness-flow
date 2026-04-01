"""Role constants for native harness."""

from harness.core.roles import ALL_ROLES, NATIVE_REVIEW_ROLES, SCORING_DIMENSIONS


def test_all_roles_empty():
    assert ALL_ROLES == frozenset()


def test_native_review_roles_defined():
    expected = {"architect", "product_owner", "engineer", "qa", "project_manager"}
    assert NATIVE_REVIEW_ROLES == expected


def test_native_review_roles_disjoint_from_all_roles():
    overlap = ALL_ROLES & NATIVE_REVIEW_ROLES
    assert not overlap, f"Unexpected overlap: {overlap}"


def test_scoring_dimensions():
    assert SCORING_DIMENSIONS == (
        "completeness",
        "quality",
        "regression",
        "design",
    )
