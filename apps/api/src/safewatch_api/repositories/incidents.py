from typing import Protocol

from pydantic import BaseModel

from safewatch_contracts.models import AgentRun, AuditEvent, IncidentRecord


class IncidentRepository(Protocol):
    def save_item(self, item: BaseModel, item_type: str) -> None:
        ...

    def list_by_incident(self, incident_id: str) -> list[dict]:
        ...

    def get_incident(self, incident_id: str) -> dict | None:
        ...


class InMemoryIncidentRepository:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def save_item(self, item: BaseModel, item_type: str) -> None:
        payload = item.model_dump(mode="json")
        payload["type"] = item_type
        payload["id"] = document_id_for(payload, item_type)
        self.items.append(payload)

    def save_incident(self, incident: IncidentRecord) -> None:
        self.save_item(incident, "incident")

    def save_agent_run(self, run: AgentRun) -> None:
        self.save_item(run, "agent_run")

    def save_audit_event(self, event: AuditEvent) -> None:
        self.save_item(event, "audit_event")

    def list_by_incident(self, incident_id: str) -> list[dict]:
        return [item for item in self.items if item.get("incident_id") == incident_id]

    def get_incident(self, incident_id: str) -> dict | None:
        for item in reversed(self.items):
            if item.get("type") == "incident" and item.get("incident_id") == incident_id:
                return item
        return None


def document_id_for(payload: dict, item_type: str) -> str:
    for key in (
        "agent_run_id",
        "audit_event_id",
        "assessment_id",
        "decision_id",
        "detection_id",
        "validation_id",
        "citation_id",
    ):
        value = payload.get(key)
        if value:
            return str(value)

    incident_id = payload.get("incident_id")
    if incident_id:
        return f"{item_type}:{incident_id}"

    raise ValueError(f"cannot derive document id for {item_type}")
