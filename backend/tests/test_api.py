from unittest.mock import patch

from app.models.db_models import RecommendationLog

def test_health_check(client):
    """
    Test the basic API health check endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "environment": "test",
    }


def test_get_history_empty(client):
    """
    Test getting history for a user with no records.
    """
    response = client.get("/api/v1/history/user_empty")
    assert response.status_code == 200
    assert response.json() == []


def test_get_history(client, db_session):
    """
    Test retrieving recommendation history.
    """
    # Setup test data
    log = RecommendationLog(
        user_id="user-history-1",
        job_title="DevOps Engineer",
        match_percentage=85.0,
        matched_skills=["AWS", "Linux"],
        missing_skills=["Terraform"],
    )
    db_session.add(log)
    db_session.commit()

    response = client.get("/api/v1/history/user-history-1")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_title"] == "DevOps Engineer"
    assert data[0]["match_percentage"] == 85.0
    assert data[0]["user_id"] == "user-history-1"


def test_toggle_bookmark(client, db_session):
    """
    Test toggling a bookmark on a recommendation.
    """
    log = RecommendationLog(
        user_id="user-bookmark-1",
        job_title="Cloud Architect",
        match_percentage=92.0,
        matched_skills=[],
        missing_skills=[],
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    # Initial state is false
    assert log.is_bookmarked is False

    # Toggle bookmark
    response = client.post(f"/api/v1/bookmark/{log.id}")
    assert response.status_code == 200
    assert response.json()["is_bookmarked"] is True

    # Check DB
    db_session.refresh(log)
    assert log.is_bookmarked is True


def test_delete_history(client, db_session):
    """
    Test deleting a user's recommendation history.
    """
    log = RecommendationLog(
        user_id="user-delete-1",
        job_title="QA Engineer",
        match_percentage=75.0,
        matched_skills=[],
        missing_skills=[],
    )
    db_session.add(log)
    db_session.commit()

    # Delete history
    response = client.delete("/api/v1/history/user-delete-1")
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    # Verify deletion
    retrieved = db_session.query(RecommendationLog).filter_by(user_id="user-delete-1").all()
    assert len(retrieved) == 0


@patch("app.api.v1.roadmap.llm_client.generate_structured")
def test_generate_roadmap_with_persistence(mock_generate, client, db_session):
    """
    Test generating a roadmap and persisting it to the DB if a recommendation_id is passed.
    """
    from app.models.schemas import RoadmapResponse, RoadmapWeek
    
    # Mock LLM response
    mock_roadmap = RoadmapResponse(
        target_job_title="Frontend Developer",
        duration_weeks=1,
        weeks=[
            RoadmapWeek(
                week=1,
                title="Basics",
                objectives=["Learn HTML/CSS"],
                skills=["HTML", "CSS"],
                resources=[]
            )
        ],
        summary="Basic frontend roadmap."
    )
    mock_generate.return_value = mock_roadmap

    # Create a recommendation record
    log = RecommendationLog(
        user_id="user-roadmap-1",
        job_title="Frontend Developer",
        match_percentage=80.0,
        matched_skills=[],
        missing_skills=["React"],
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    # Call generate roadmap
    payload = {
        "target_job_title": "Frontend Developer",
        "missing_skills": ["React"],
        "current_skills": ["HTML", "CSS"],
        "weeks": 1,
        "recommendation_id": log.id
    }
    
    response = client.post("/api/v1/roadmap/generate", json=payload)
    assert response.status_code == 200

    # Verify it was saved to the DB
    db_session.refresh(log)
    assert log.roadmap is not None
    assert log.roadmap["target_job_title"] == "Frontend Developer"
