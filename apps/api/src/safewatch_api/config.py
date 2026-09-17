import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    environment: str = "local"
    policy_version: str = "governance-policy-v1"
    risk_policy_version: str = "risk-policy-v1"
    vision_model_version: str = "mock-vision-v1"
    document_model_version: str = "mock-document-v1"
    rag_index_version: str = "rag-index-v1"
    prompt_version: str = "prompt-v1"

    cosmos_endpoint: str | None = None
    cosmos_database: str = "safewatch"
    cosmos_container: str = "incidents"

    azure_ai_vision_endpoint: str | None = None
    azure_ai_vision_api_key: str | None = None
    azure_ai_vision_api_version: str = "2024-02-01"

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_chat_deployment: str = "chat-safewatch-v1"
    azure_openai_embedding_deployment: str = "embed-safewatch-v1"
    azure_openai_embedding_api_version: str = "2024-02-01"
    storage_account_name: str | None = None
    document_intelligence_endpoint: str | None = None
    document_intelligence_model_id: str = "prebuilt-layout"
    azure_ai_search_endpoint: str | None = None
    azure_ai_search_index_name: str = "safewatch-regulations-v1"
    azure_ai_search_api_version: str = "2024-07-01"

    applicationinsights_connection_string: str | None = Field(default=None)
    langsmith_tracing: bool = False
    langsmith_project: str = "safewatch-ai-v1"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langsmith_workspace_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("SAFEWATCH_ENVIRONMENT", "local"),
        policy_version=os.getenv("SAFEWATCH_POLICY_VERSION", "governance-policy-v1"),
        risk_policy_version=os.getenv("SAFEWATCH_RISK_POLICY_VERSION", "risk-policy-v1"),
        vision_model_version=os.getenv("SAFEWATCH_VISION_MODEL_VERSION", "mock-vision-v1"),
        document_model_version=os.getenv("SAFEWATCH_DOCUMENT_MODEL_VERSION", "mock-document-v1"),
        rag_index_version=os.getenv("SAFEWATCH_RAG_INDEX_VERSION", "rag-index-v1"),
        prompt_version=os.getenv("SAFEWATCH_PROMPT_VERSION", "prompt-v1"),
        cosmos_endpoint=os.getenv("SAFEWATCH_COSMOS_ENDPOINT"),
        cosmos_database=os.getenv("SAFEWATCH_COSMOS_DATABASE", "safewatch"),
        cosmos_container=os.getenv("SAFEWATCH_COSMOS_CONTAINER", "incidents"),
        azure_ai_vision_endpoint=os.getenv("SAFEWATCH_AZURE_AI_VISION_ENDPOINT"),
        azure_ai_vision_api_key=os.getenv("SAFEWATCH_AZURE_AI_VISION_API_KEY"),
        azure_ai_vision_api_version=os.getenv("SAFEWATCH_AZURE_AI_VISION_API_VERSION", "2024-02-01"),
        azure_openai_endpoint=os.getenv("SAFEWATCH_AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=os.getenv("SAFEWATCH_AZURE_OPENAI_API_KEY"),
        azure_openai_chat_deployment=os.getenv("SAFEWATCH_AZURE_OPENAI_CHAT_DEPLOYMENT", "chat-safewatch-v1"),
        azure_openai_embedding_deployment=os.getenv(
            "SAFEWATCH_AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
            "embed-safewatch-v1",
        ),
        azure_openai_embedding_api_version=os.getenv("SAFEWATCH_AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-01"),
        storage_account_name=os.getenv("SAFEWATCH_STORAGE_ACCOUNT_NAME"),
        document_intelligence_endpoint=os.getenv("SAFEWATCH_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        document_intelligence_model_id=os.getenv("SAFEWATCH_DOCUMENT_INTELLIGENCE_MODEL_ID", "prebuilt-layout"),
        azure_ai_search_endpoint=os.getenv("SAFEWATCH_AZURE_AI_SEARCH_ENDPOINT"),
        azure_ai_search_index_name=os.getenv("SAFEWATCH_AZURE_AI_SEARCH_INDEX_NAME", "safewatch-regulations-v1"),
        azure_ai_search_api_version=os.getenv("SAFEWATCH_AZURE_AI_SEARCH_API_VERSION", "2024-07-01"),
        applicationinsights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        langsmith_tracing=os.getenv("LANGSMITH_TRACING", "false").lower() == "true",
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "safewatch-ai-v1"),
        langsmith_endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
        langsmith_workspace_id=os.getenv("LANGSMITH_WORKSPACE_ID"),
    )
