"""
Tests for the Mergington High School Activities API
Uses AAA (Arrange-Act-Assert) testing pattern
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        # Arrange
        # (No setup needed - using default activities)
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert isinstance(data, dict)
        assert "Soccer" in data
        assert "Basketball" in data
        assert "description" in data["Soccer"]
        assert "schedule" in data["Soccer"]
        assert "max_participants" in data["Soccer"]
        assert "participants" in data["Soccer"]
    
    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        # Arrange
        # (No setup needed)
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
            assert isinstance(activity_details["max_participants"], int)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        # Arrange
        email = "test@mergington.edu"
        activity = "Soccer"
        
        # Act
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]
    
    def test_signup_duplicate_prevention(self, client):
        """Test that duplicate signups are prevented"""
        # Arrange
        email = "duplicate@mergington.edu"
        activity = "Soccer"
        
        # Act - First signup
        response1 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        
        # Assert - First signup succeeds
        assert response1.status_code == 200
        
        # Act - Second signup attempt
        response2 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        data2 = response2.json()
        
        # Assert - Second signup fails
        assert response2.status_code == 400
        assert "already signed up" in data2["detail"].lower()
    
    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        # Arrange
        email = "test@mergington.edu"
        invalid_activity = "NonExistentActivity"
        
        # Act
        response = client.post(
            f"/activities/{invalid_activity}/signup?email={email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_students(self, client):
        """Test multiple students can sign up for the same activity"""
        # Arrange
        activity = "Chess Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        # Act
        responses = []
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            responses.append(response)
        
        # Assert
        for response in responses:
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for email in emails:
            assert email in activities_data[activity]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # Arrange
        email = "remove-test@mergington.edu"
        activity = "Soccer"
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Act
        response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert "Removed" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing a participant that doesn't exist"""
        # Arrange
        activity = "Soccer"
        nonexistent_email = "nonexistent@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity}/participants/{nonexistent_email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "not found" in data["detail"].lower()
    
    def test_remove_participant_invalid_activity(self, client):
        """Test removing participant from non-existent activity"""
        # Arrange
        invalid_activity = "NonExistentActivity"
        email = "test@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{invalid_activity}/participants/{email}"
        )
        data = response.json()
        
        # Assert
        assert response.status_code == 404
        assert "not found" in data["detail"].lower()
    
    def test_remove_existing_participant(self, client):
        """Test removing a pre-existing participant"""
        # Arrange
        activity = "Soccer"
        existing_email = "alex@mergington.edu"  # Exists by default
        
        # Act
        response = client.delete(
            f"/activities/{activity}/participants/{existing_email}"
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert existing_email not in activities_data[activity]["participants"]


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_signup_and_removal_workflow(self, client):
        """Test full workflow: signup, verify, remove, verify"""
        # Arrange
        email = "workflow-test@mergington.edu"
        activity = "Robotics Club"
        
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Act - Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        
        # Assert - Signup successful
        assert signup_response.status_code == 200
        after_signup = client.get("/activities")
        after_signup_count = len(after_signup.json()[activity]["participants"])
        assert after_signup_count == initial_count + 1
        assert email in after_signup.json()[activity]["participants"]
        
        # Act - Remove
        remove_response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        
        # Assert - Removal successful
        assert remove_response.status_code == 200
        after_removal = client.get("/activities")
        after_removal_count = len(after_removal.json()[activity]["participants"])
        assert after_removal_count == initial_count
        assert email not in after_removal.json()[activity]["participants"]
    
    def test_multiple_activities_signup(self, client):
        """Test that one student can sign up for multiple activities"""
        # Arrange
        email = "multi-activity@mergington.edu"
        activities_list = ["Soccer", "Chess Club", "Art Club"]
        
        # Act
        responses = []
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            responses.append(response)
        
        # Assert
        for response in responses:
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_list:
            assert email in activities_data[activity]["participants"]
    
    def test_signup_and_duplicate_across_refresh(self, client):
        """Test that duplicate prevention persists across multiple checks"""
        # Arrange
        email = "persistent@mergington.edu"
        activity = "Art Club"
        
        # Act - Initial signup
        first_signup = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        
        # Assert - First signup works
        assert first_signup.status_code == 200
        
        # Act - Attempt duplicate signup multiple times
        duplicate_attempts = [
            client.post(f"/activities/{activity}/signup?email={email}")
            for _ in range(3)
        ]
        
        # Assert - All duplicates rejected
        for attempt in duplicate_attempts:
            assert attempt.status_code == 400
            assert "already signed up" in attempt.json()["detail"].lower()
        
        # Verify only one instance exists
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity]["participants"]
        assert participants.count(email) == 1
