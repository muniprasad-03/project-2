from app.models.db_models import RecommendationLog

def test_create_recommendation_log(db_session):
    """
    Test creating a RecommendationLog record.
    """
    log = RecommendationLog(
        user_id="test-user-123",
        job_title="Software Engineer",
        match_percentage=95.5,
        matched_skills=["Python", "SQL"],
        missing_skills=["Docker", "Kubernetes"],
    )
    
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    
    assert log.id is not None
    assert log.user_id == "test-user-123"
    assert log.job_title == "Software Engineer"
    assert log.match_percentage == 95.5
    assert log.matched_skills == ["Python", "SQL"]
    assert log.missing_skills == ["Docker", "Kubernetes"]
    assert log.roadmap is None
    assert log.is_bookmarked is False
    assert log.timestamp is not None


def test_bookmark_recommendation_log(db_session):
    """
    Test toggling the bookmark state of a RecommendationLog.
    """
    log = RecommendationLog(
        user_id="test-user-123",
        job_title="Data Scientist",
        match_percentage=88.0,
        matched_skills=[],
        missing_skills=[],
    )
    
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    
    assert log.is_bookmarked is False
    
    # Toggle to true
    log.is_bookmarked = True
    db_session.commit()
    db_session.refresh(log)
    
    assert log.is_bookmarked is True


def test_delete_recommendation_log(db_session):
    """
    Test deleting a RecommendationLog.
    """
    log = RecommendationLog(
        user_id="delete-user-123",
        job_title="Backend Developer",
        match_percentage=90.0,
        matched_skills=[],
        missing_skills=[],
    )
    
    db_session.add(log)
    db_session.commit()
    
    # Ensure it exists
    retrieved = db_session.query(RecommendationLog).filter_by(user_id="delete-user-123").first()
    assert retrieved is not None
    
    # Delete it
    db_session.delete(retrieved)
    db_session.commit()
    
    # Ensure it's gone
    retrieved = db_session.query(RecommendationLog).filter_by(user_id="delete-user-123").first()
    assert retrieved is None
