from safewatch_api.config import Settings
from safewatch_api.repositories.cosmos import CosmosIncidentRepository
from safewatch_api.repositories.incidents import InMemoryIncidentRepository, IncidentRepository


def build_incident_repository(settings: Settings) -> IncidentRepository:
    if settings.cosmos_endpoint:
        return CosmosIncidentRepository(
            endpoint=settings.cosmos_endpoint,
            database_name=settings.cosmos_database,
            container_name=settings.cosmos_container,
        )
    return InMemoryIncidentRepository()
