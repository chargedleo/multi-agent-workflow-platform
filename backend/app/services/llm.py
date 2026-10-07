"""LLM Factory and Abstraction Service.

Provides a unified interface for instantiating LLMs across providers
(OpenAI, Azure, Ollama, OpenAI-compatible APIs, and Mock for local/testing).
Supports structured Pydantic outputs with resilient fallbacks.
"""

from typing import Any, List, Optional, Type, TypeVar
import json
import logging
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.models.schemas import Plan, ResearchResult, WorkflowResponse

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class MockChatModel(BaseChatModel):
    """Deterministic Mock Chat Model for testing and offline development.

    Satisfies LangChain BaseChatModel and supports with_structured_output.
    """

    model_name: str = "mock-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = "Mock response generated for input query."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    def with_structured_output(self, schema: Type[T], **kwargs: Any) -> Any:
        """Return a runnable mock wrapper that returns a valid instance of schema."""
        class MockStructuredRunnable:
            def __init__(self, target_schema: Type[T]):
                self.target_schema = target_schema

            def invoke(self, input_val: Any, config: Optional[dict] = None) -> T:
                # Extract query or content from input
                query_str = ""
                if isinstance(input_val, str):
                    query_str = input_val
                elif isinstance(input_val, list):
                    query_str = " ".join(getattr(m, "content", str(m)) for m in input_val)
                elif isinstance(input_val, dict):
                    query_str = str(input_val)

                if issubclass(self.target_schema, Plan):
                    return self.target_schema(
                        goal=f"Analyze and address: {query_str[:120]}...",
                        steps=[
                            "Analyze core requirements and architectural context",
                            "Investigate key trade-offs and operational capabilities",
                            "Assess scalability, data consistency, and maintenance overhead",
                            "Synthesize findings and deliver actionable recommendations",
                        ],
                    )

                if issubclass(self.target_schema, ResearchResult):
                    return self.target_schema(
                        findings=[
                            "Relational databases provide strong ACID consistency and strict relational schemas ideal for transactional integrity.",
                            "Document databases offer flexible schemas and horizontal partitioning suitable for high-ingestion, unstructured datasets.",
                            "Operational complexity is lower with managed relational offerings when queries require complex joins and aggregations.",
                        ],
                        assumptions=[
                            "Assumes a modern cloud hosting environment with standard managed infrastructure.",
                            "Assumes typical early-to-mid stage startup scalability requirements.",
                        ],
                        unanswered_questions=[
                            "What is the projected write-to-read ratio and primary query access pattern?",
                            "Are there multi-region regulatory or data sovereignty constraints?",
                        ],
                    )

                if issubclass(self.target_schema, WorkflowResponse):
                    return self.target_schema(
                        request_id=kwargs.get("request_id", "mock-req-001"),
                        answer=(
                            f"Based on the analysis of your query '{query_str[:80]}...': "
                            "PostgreSQL is strongly recommended as the default database for most SaaS startups due to "
                            "its robust ACID guarantees, rich indexing, support for JSONB, and mature ecosystem. "
                            "MongoDB is beneficial if your data model is strictly hierarchical, schema-free, "
                            "or requires rapid horizontal sharding across distributed clusters."
                        ),
                        key_points=[
                            "PostgreSQL offers superior data integrity, relational constraints, and flexible JSONB querying.",
                            "MongoDB provides rapid prototyping for polymorphic documents and out-of-the-box horizontal scaling.",
                            "For a SaaS startup, starting with PostgreSQL reduces early schema technical debt.",
                        ],
                        confidence=0.95,
                    )

                # Generic mock fallback
                try:
                    return self.target_schema.model_validate({})
                except Exception:
                    raise ValueError(f"Cannot generate mock data for schema {self.target_schema}")

            async def ainvoke(self, input_val: Any, config: Optional[dict] = None) -> T:
                return self.invoke(input_val, config)

        return MockStructuredRunnable(schema)


def get_llm(
    settings: Optional[Settings] = None,
    override_provider: Optional[str] = None,
) -> BaseChatModel:
    """Instantiate and return the configured LLM client.

    Args:
        settings: Application settings (defaults to cached settings).
        override_provider: Optional provider override for testing or specific tasks.

    Returns:
        BaseChatModel: Configured LangChain chat model.
    """
    cfg = settings or get_settings()
    provider = (override_provider or cfg.LLM_PROVIDER).lower()

    if provider == "mock":
        logger.info("Using deterministic MockChatModel (provider: mock)")
        return MockChatModel()

    if provider in ("openai", "ollama", "azure_openai"):
        api_key = cfg.LLM_API_KEY or "dummy-key"
        base_url = cfg.LLM_BASE_URL if cfg.LLM_BASE_URL else None

        logger.info(
            f"Configuring ChatOpenAI with model={cfg.LLM_MODEL}, provider={provider}, base_url={base_url or 'default'}"
        )
        return ChatOpenAI(
            model=cfg.LLM_MODEL,
            api_key=api_key,
            base_url=base_url,
            temperature=cfg.LLM_TEMPERATURE,
        )

    # Default fallback
    logger.warning(f"Unrecognized provider '{provider}'. Falling back to MockChatModel.")
    return MockChatModel()


async def invoke_structured(
    llm: BaseChatModel,
    prompt: Any,
    schema: Type[T],
) -> T:
    """Invoke an LLM with structured output, including robust fallback parsing.

    Args:
        llm: Configured BaseChatModel
        prompt: LangChain prompt messages or text
        schema: Target Pydantic model

    Returns:
        Validated instance of schema
    """
    # 1. Attempt native structured output via with_structured_output
    try:
        structured_llm = llm.with_structured_output(schema)
        result = await structured_llm.ainvoke(prompt)
        if isinstance(result, schema):
            return result
        if isinstance(result, dict):
            return schema.model_validate(result)
    except Exception as err:
        logger.warning(
            f"Native with_structured_output failed ({type(err).__name__}: {err}). Attempting fallback JSON parsing."
        )

    # 2. Resilient fallback using PydanticOutputParser
    try:
        parser = PydanticOutputParser(pydantic_object=schema)
        format_instructions = parser.get_format_instructions()

        fallback_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Respond ONLY with a valid JSON object matching this schema. "
            f"Do not include any markdown wrappers or explanatory text.\n"
            f"{format_instructions}"
        )

        response = await llm.ainvoke(fallback_prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Clean potential markdown fences
        clean_json = content.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        return parser.parse(clean_json)
    except Exception as parse_err:
        logger.error(f"Fallback parsing also failed for {schema.__name__}: {parse_err}")
        raise ValueError(f"Failed to generate structured output for {schema.__name__}: {parse_err}") from parse_err
