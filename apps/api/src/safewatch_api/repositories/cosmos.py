from typing import Any

from pydantic import BaseModel

from safewatch_api.repositories.incidents import document_id_for


class CosmosIncidentRepository:
    def __init__(self, endpoint: str, database_name: str, container_name: str) -> None:
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        client = CosmosClient(endpoint, credential=credential)
        self.container = client.get_database_client(database_name).get_container_client(container_name)

    def save_item(self, item: BaseModel, item_type: str) -> None:
        payload: dict[str, Any] = item.model_dump(mode="json")
        payload["type"] = item_type
        payload["id"] = payload.get("id") or document_id_for(payload, item_type)
        self.container.upsert_item(payload)

    def list_by_incident(self, incident_id: str) -> list[dict]:
        query = "SELECT * FROM c WHERE c.incident_id = @incident_id"
        parameters = [{"name": "@incident_id", "value": incident_id}]
        return list(
            self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=incident_id,
            )
        )

    def get_incident(self, incident_id: str) -> dict | None:
        try:
            return self.container.read_item(
                item=f"incident:{incident_id}",
                partition_key=incident_id,
            )
        except Exception:
            return None
