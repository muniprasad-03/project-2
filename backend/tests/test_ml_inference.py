from __future__ import annotations

import pytest

from app.ml.inference import match_careers


def test_match_careers_returns_results():
    """
    The recommendation engine should return at least one
    career recommendation for a valid skill list.
    """
    skills = [
        "Python",
        "SQL",
        "Machine Learning",
        "Statistics",
        "Problem Solving",
    ]

    results = match_careers(
        user_skills=skills,
        top_k=5,
    )

    assert isinstance(results, list)
    assert len(results) > 0


def test_match_careers_respects_top_k():
    """
    The number of returned recommendations should not exceed
    the requested top_k value.
    """
    skills = [
        "Python",
        "SQL",
        "Machine Learning",
    ]

    results = match_careers(
        user_skills=skills,
        top_k=3,
    )

    assert len(results) <= 3


def test_match_percentage_is_valid():
    """
    Every recommendation must have a match percentage between
    0 and 100.
    """
    skills = [
        "Python",
        "SQL",
        "Machine Learning",
        "Statistics",
    ]

    results = match_careers(
        user_skills=skills,
        top_k=5,
    )

    assert len(results) > 0

    for result in results:
        assert "match_percentage" in result

        percentage = result["match_percentage"]

        assert isinstance(
            percentage,
            (int, float),
        )

        assert 0 <= percentage <= 100


def test_required_result_fields_exist():
    """
    Every recommendation should contain the fields expected
    by the future FastAPI recommendation endpoint.
    """
    skills = [
        "Python",
        "SQL",
        "Machine Learning",
    ]

    results = match_careers(
        user_skills=skills,
        top_k=3,
    )

    assert len(results) > 0

    required_fields = {
        "onet_soc_code",
        "job_title",
        "description",
        "match_percentage",
        "matched_skills",
        "missing_skills",
        "text_similarity",
        "skill_coverage",
        "riasec_similarity",
    }

    for result in results:
        assert required_fields.issubset(
            result.keys()
        )


def test_matched_skills_is_list():
    """
    matched_skills must always be returned as a list.
    """
    results = match_careers(
        user_skills=[
            "Python",
            "SQL",
        ],
        top_k=5,
    )

    assert len(results) > 0

    for result in results:
        assert isinstance(
            result["matched_skills"],
            list,
        )


def test_missing_skills_is_list():
    """
    missing_skills must always be returned as a list.
    """
    results = match_careers(
        user_skills=[
            "Python",
            "SQL",
        ],
        top_k=5,
    )

    assert len(results) > 0

    for result in results:
        assert isinstance(
            result["missing_skills"],
            list,
        )

        for skill in result["missing_skills"]:
            assert isinstance(
                skill,
                str,
            )


def test_empty_skills_are_rejected():
    """
    The recommendation engine should reject an empty skill list.
    """
    with pytest.raises(ValueError):
        match_careers(
            user_skills=[],
            top_k=5,
        )


def test_invalid_top_k_is_rejected():
    """
    top_k must be at least 1.
    """
    with pytest.raises(ValueError):
        match_careers(
            user_skills=[
                "Python",
            ],
            top_k=0,
        )


def test_duplicate_skills_do_not_break_engine():
    """
    Duplicate user skills should be handled safely.
    """
    results = match_careers(
        user_skills=[
            "Python",
            "Python",
            "SQL",
            "SQL",
        ],
        top_k=5,
    )

    assert isinstance(results, list)
    assert len(results) > 0


def test_results_are_sorted_by_match_percentage():
    """
    Recommendations should be ordered from highest match
    percentage to lowest.
    """
    results = match_careers(
        user_skills=[
            "Python",
            "SQL",
            "Machine Learning",
            "Statistics",
        ],
        top_k=10,
    )

    assert len(results) > 0

    percentages = [
        result["match_percentage"]
        for result in results
    ]

    assert percentages == sorted(
        percentages,
        reverse=True,
    )


def test_riasec_profile_can_be_used():
    """
    Supplying a RIASEC profile should not break the
    recommendation engine.
    """
    user_riasec = {
        "Realistic": 2.0,
        "Investigative": 5.0,
        "Artistic": 2.0,
        "Social": 3.0,
        "Enterprising": 3.0,
        "Conventional": 4.0,
    }

    results = match_careers(
        user_skills=[
            "Python",
            "SQL",
            "Machine Learning",
        ],
        top_k=5,
        user_riasec=user_riasec,
    )

    assert isinstance(results, list)
    assert len(results) > 0

    for result in results:
        assert 0 <= result["riasec_similarity"] <= 1


def test_missing_skill_values_are_strings():
    """
    Every missing skill returned by the engine must be a string.
    """
    results = match_careers(
        user_skills=[
            "Python",
            "SQL",
            "Machine Learning",
        ],
        top_k=5,
    )

    assert len(results) > 0

    for result in results:
        for skill in result["missing_skills"]:
            assert isinstance(
                skill,
                str,
            )