from alembic import command


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_migrations_match_the_models(alembic_config):
    # Fails when a model changed without a new migration.
    command.check(alembic_config)
