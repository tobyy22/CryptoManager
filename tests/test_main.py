import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User
from main import app, get_db
from fastapi.testclient import TestClient


TEST_DATABASE_URL = (
    "postgresql://test_user:test_password@test_postgres:5432/test_database"
)

test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def test_create_user(test_db):
    user_data = {"name": "testuser"}

    response = client.post("/users/", json=user_data)

    assert response.status_code == 200
    assert response.json()["message"] == "User created"
    assert "api_key" in response.json()


def test_create_duplicate_user(test_db):
    user_data = {"name": "testuser"}

    response1 = client.post("/users/", json=user_data)
    assert response1.status_code == 200

    response2 = client.post("/users/", json=user_data)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "User already exists"


def test_create_and_update_user(test_db):

    user_data = {"name": "testuser"}

    create_response = client.post("/users/", json=user_data)

    assert create_response.status_code == 200
    assert create_response.json()["message"] == "User created"

    api_key = create_response.json()["api_key"]

    update_data = {"old_name": "testuser", "new_name": "updated_user"}

    update_response = client.put(
        "/users/",
        json=update_data,
        headers={"api-key": api_key},
    )

    assert update_response.status_code == 200
    assert update_response.json()["message"] == "User name updated successfully"
    assert update_response.json()["new_name"] == "updated_user"

    updated_user = test_db.query(User).filter(User.name == "updated_user").first()

    assert updated_user is not None
    assert updated_user.name == "updated_user"


def test_create_and_delete_user(test_db):
    user_data = {"name": "testuser"}

    create_response = client.post("/users/", json=user_data)
    assert create_response.status_code == 200
    api_key = create_response.json()["api_key"]

    delete_response = client.delete(url="/users/testuser", headers={"api-key": api_key})
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "User deleted successfully"

    second_delete_response = client.delete(
        "/users/testuser", headers={"api-key": api_key}
    )
    assert second_delete_response.status_code == 403
    assert second_delete_response.json()["detail"] == "Invalid username or API key"


def test_user_balance_update_and_networth(test_db):
    # Step 1: Create a user
    response = client.post("/users/", json={"name": "testuser"})
    assert response.status_code == 200
    user_api_key = response.json()["api_key"]

    response = client.post(
        "/balances/",
        json={"name": "testuser", "symbol": "dasdasdsa", "amount": 1},
        headers={"api-key": user_api_key},
    )
    assert response.status_code == 404

    response = client.post(
        "/balances/",
        json={"name": "testuser", "symbol": "bitcoin", "amount": 1},
        headers={"api-key": user_api_key},
    )
    assert response.status_code == 200
    assert "Updated testuser's BITCOIN balance" in response.json()["message"]

    response = client.put(
        "/users/",
        json={"old_name": "testuser", "new_name": "newtestuser"},
        headers={"api-key": user_api_key},
    )
    assert response.status_code == 200
    assert response.json()["new_name"] == "newtestuser"

    response = client.get(
        "/users/testuser/networth",
        params={"currency": "usd"},
        headers={"api-key": user_api_key},
    )
    assert response.status_code == 403

    response = client.get(
        "/users/newtestuser/networth",
        params={"currency": "usd"},
        headers={"api-key": user_api_key},
    )
    assert response.status_code == 200
    assert "net_worth" in response.json()
