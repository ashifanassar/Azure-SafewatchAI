# SafeWatch AI v1 Implementation Roadmap

## Build Philosophy

Build the smallest complete enterprise loop first, then improve each agent.

The first successful demo should show:

1. A safety image and permit are submitted.
2. PPE/document issues are detected.
3. A regulation is retrieved.
4. Risk is scored.
5. Governance rules select the approval path.
6. A reviewer approves or escalates.
7. The audit trail proves what happened and why.

## Sprint Plan

### Sprint 1: Foundation

Deliverables:

- Repository structure.
- API skeleton.
- Shared contracts/types.
- Incident, evidence, agent result, approval task, and audit event schema.
- Basic Operations Console and Governance Dashboard shells.

Acceptance criteria:

- A user can create a draft incident.
- Evidence metadata can be registered.
- Incident data can be read back through the API.

### Sprint 2: Agent Workflow

Deliverables:

- Orchestrator service.
- Vision Agent interface with stub or first model integration.
- Document Validation Agent interface with stub or first validator.
- Compliance RAG Agent with indexed sample OSHAD / TRAKHEES / MOMRA / ISO 45001 content.
- Agent result persistence.

Acceptance criteria:

- Running analysis creates structured outputs for vision, document validation, and compliance.
- Every agent call is linked to the same `correlation_id`.

### Sprint 3: Risk and Governance

Deliverables:

- Risk scoring package.
- Governance policy engine.
- Approval workflow.
- Role-based approval routing.
- Audit trail events.

Acceptance criteria:

- Low, medium, high, and critical incidents route differently.
- Expired permit blocks incident closure.
- Human decisions are recorded with reviewer, timestamp, and reason.

### Sprint 4: UI and Demo Readiness

Deliverables:

- Operations Console incident workflow.
- Governance Dashboard metrics.
- Incident detail page with audit trail.
- Seed data for demo scenarios.
- Demo script.

Acceptance criteria:

- A complete v1 scenario can be demonstrated end to end.
- The governance dashboard shows risk distribution, pending approvals, escalations, and override rate.

## Suggested Ownership Split

| Area | Owner A | Owner B |
| --- | --- | --- |
| Architecture and contracts | Shared | Shared |
| Vision/PPE workflow | Primary | Support |
| Compliance RAG | Support | Primary |
| Document validation | Shared | Shared |
| Risk scoring | Primary | Review |
| Governance policy | Review | Primary |
| Operations Console | Primary | Support |
| Governance Dashboard | Support | Primary |
| Demo and presentation | Shared | Shared |

## Demo Scenarios

### Scenario 1: Low Risk

- Image shows worker with required PPE.
- Permit is valid.
- No violation or minor observation.
- System auto-logs the incident.

### Scenario 2: High Risk

- Image shows missing helmet in active work zone.
- Permit is valid.
- Risk band is high.
- HSE Manager approval is required.

### Scenario 3: Critical Risk

- Image shows missing harness during elevated work.
- Permit is expired.
- Risk band is critical.
- Closure is blocked.
- Escalation Committee review is required.

## Engineering Priorities

1. Keep deterministic decisions outside the LLM.
2. Persist every intermediate result.
3. Make citations mandatory for compliance assessment.
4. Make policy versioning visible in the audit trail.
5. Optimize for a credible enterprise demo before adding advanced prediction.
