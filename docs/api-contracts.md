# SafeWatch AI v1 API and Tool Contracts

## 1. REST API Surface

### `POST /incidents`

Create a new incident draft.

Request:

```json
{
  "site_id": "site_001",
  "zone_id": "zone_elevated_04",
  "work_type": "elevated_work",
  "contractor_id": "contractor_017",
  "description": "Worker observed on scaffold without visible harness."
}
```

Response:

```json
{
  "incident_id": "inc_20260713_0001",
  "status": "draft"
}
```

### `POST /incidents/{incident_id}/evidence`

Upload or register evidence.

Request:

```json
{
  "type": "image",
  "file_name": "scaffold-zone-4.jpg",
  "content_type": "image/jpeg"
}
```

Response:

```json
{
  "evidence_id": "ev_001",
  "upload_url": "https://storage.example/upload-token",
  "blob_uri": "blob://safewatch/inc_20260713_0001/scaffold-zone-4.jpg"
}
```

### `POST /incidents/{incident_id}/analyze`

Start the agent workflow.

Response:

```json
{
  "incident_id": "inc_20260713_0001",
  "workflow_run_id": "run_001",
  "status": "analysis_started"
}
```

### `GET /incidents/{incident_id}`

Return incident details, evidence, agent results, risk score, governance route, and approval status.

### `GET /approvals`

Return pending approval tasks filtered by current user role.

Query parameters:

- `status`
- `required_role`
- `site_id`
- `risk_band`

### `POST /approvals/{approval_task_id}/decision`

Submit a human decision.

Request:

```json
{
  "decision": "approve",
  "decision_reason": "Confirmed missing harness during elevated work. Immediate corrective action assigned.",
  "override": false
}
```

Response:

```json
{
  "approval_task_id": "approval_001",
  "incident_id": "inc_20260713_0001",
  "status": "approved"
}
```

### `GET /dashboard/operations`

Return operational metrics for the Operations Console.

### `GET /dashboard/governance`

Return governance and audit metrics.

## 2. MCP-Style Tool Contracts

### `analyze_site_image`

Purpose: detect PPE violations in static image evidence.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "image_uri": "blob://safewatch/inc_20260713_0001/scaffold-zone-4.jpg",
  "site_context": {
    "site_id": "site_001",
    "zone_id": "zone_elevated_04",
    "work_type": "elevated_work"
  }
}
```

Output:

```json
{
  "agent_name": "vision-agent",
  "model_version": "ppe-detector-v1",
  "workers_detected": 2,
  "violations": [
    {
      "violation_type": "missing_harness",
      "severity": "critical",
      "confidence": 0.91,
      "worker_ref": "worker_1"
    }
  ],
  "annotated_image_uri": "blob://safewatch/inc_20260713_0001/annotated.jpg"
}
```

### `validate_safety_document`

Purpose: validate permit or safety document evidence.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "document_uri": "blob://safewatch/inc_20260713_0001/permit.pdf",
  "expected_document_type": "permit_to_work",
  "incident_context": {
    "work_type": "elevated_work",
    "incident_time": "2026-07-13T08:30:00Z"
  }
}
```

Output:

```json
{
  "agent_name": "document-validation-agent",
  "document_type": "permit_to_work",
  "validation_status": "failed",
  "extracted_fields": {
    "permit_number": "PTW-4481",
    "work_type": "elevated_work",
    "expiry_time": "2026-07-12T18:00:00Z",
    "approver": "HSE Supervisor"
  },
  "issues": [
    {
      "issue_type": "expired_permit",
      "severity": "high",
      "message": "Permit expired before incident time."
    }
  ]
}
```

### `retrieve_compliance_clauses`

Purpose: retrieve applicable regulatory clauses.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "query": "missing fall protection harness during elevated work with expired permit",
  "sources": ["OSHAD", "TRAKHEES", "MOMRA", "ISO_45001"],
  "top_k": 5
}
```

Output:

```json
{
  "agent_name": "compliance-rag-agent",
  "retrieval_index_version": "safety-index-v1",
  "clauses": [
    {
      "source": "OSHAD",
      "clause_id": "OSHAD-SF-4.2",
      "title": "Working at Height Controls",
      "excerpt": "Employers shall ensure fall protection controls are used for elevated work.",
      "score": 0.86
    }
  ]
}
```

### `generate_compliance_assessment`

Purpose: produce a grounded compliance interpretation using retrieved clauses.

Output:

```json
{
  "agent_name": "compliance-rag-agent",
  "prompt_version": "compliance-assessment-v1",
  "assessment": "The incident indicates a likely fall-protection compliance breach because elevated work was performed without visible harness protection.",
  "citations": [
    {
      "source": "OSHAD",
      "clause_id": "OSHAD-SF-4.2"
    }
  ],
  "recommended_corrective_action": "Stop elevated work, verify fall protection, renew permit-to-work, and require HSE manager review."
}
```

### `calculate_risk_score`

Purpose: produce deterministic risk score and explanation.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "violations": [
    {
      "violation_type": "missing_harness",
      "severity": "critical",
      "confidence": 0.91
    }
  ],
  "document_validation": {
    "validation_status": "failed",
    "issues": ["expired_permit"]
  },
  "compliance": {
    "regulatory_severity": "high"
  },
  "context": {
    "work_zone_risk": "high",
    "workers_exposed": 1,
    "recent_related_incidents": 0
  }
}
```

Output:

```json
{
  "agent_name": "risk-scoring-agent",
  "policy_version": "risk-policy-v1",
  "risk_score": 87,
  "risk_band": "critical",
  "factor_breakdown": {
    "ppe_severity": 30,
    "work_zone_risk": 18,
    "permit_status": 20,
    "regulatory_severity": 14,
    "workers_exposed": 5,
    "recent_related_incidents": 0
  },
  "explanation": "Critical score caused by missing fall protection during elevated work and expired permit-to-work."
}
```

### `generate_incident_report`

Purpose: produce the cited reviewer packet after deterministic risk and governance decisions are complete.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "vision_result_ref": "agent_result_vision_001",
  "document_result_ref": "agent_result_document_001",
  "compliance_result_ref": "agent_result_compliance_001",
  "risk_result_ref": "agent_result_risk_001",
  "governance_result_ref": "agent_result_governance_001"
}
```

Output:

```json
{
  "agent_name": "report-agent",
  "prompt_version": "incident-report-v1",
  "report": {
    "summary": "Worker was detected without fall-protection harness during elevated work. Permit-to-work was expired.",
    "risk_band": "critical",
    "approval_route": "escalation_committee",
    "required_actions": [
      "renew_permit_to_work",
      "verify_fall_protection",
      "committee_review"
    ],
    "citations": [
      {
        "source": "OSHAD",
        "clause_id": "OSHAD-SF-4.2"
      }
    ]
  }
}
```

### `evaluate_governance_policy`

Purpose: apply deterministic approval and closure rules.

Input:

```json
{
  "correlation_id": "corr_001",
  "incident_id": "inc_20260713_0001",
  "risk_score": 87,
  "risk_band": "critical",
  "document_validation_status": "failed",
  "violation_types": ["missing_harness"],
  "work_type": "elevated_work",
  "citations_present": true
}
```

Output:

```json
{
  "agent_name": "governance-agent",
  "policy_version": "governance-policy-v1",
  "approval_level": "escalation_committee",
  "blocked_actions": ["close_incident"],
  "required_actions": [
    "renew_permit_to_work",
    "verify_fall_protection",
    "committee_review"
  ],
  "triggered_rules": [
    "critical_risk_requires_committee",
    "expired_permit_blocks_closure",
    "elevated_work_missing_harness_minimum_high"
  ]
}
```
