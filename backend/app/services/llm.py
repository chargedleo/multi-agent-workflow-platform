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
                    human_msgs = [m for m in input_val if getattr(m, "type", "") == "human" or getattr(m, "__class__", "").__name__ == "HumanMessage"]
                    if human_msgs:
                        query_str = " ".join(getattr(m, "content", str(m)) for m in human_msgs)
                    else:
                        query_str = " ".join(getattr(m, "content", str(m)) for m in input_val)
                elif isinstance(input_val, dict):
                    query_str = str(input_val)

                # Extract pure user query text if structured prompt wrapper was used
                if "User Query:" in query_str:
                    user_text = query_str.split("User Query:")[1].split("\n\n")[0].strip()
                else:
                    user_text = query_str

                if self.target_schema.__name__ == "AnalysisDecision":
                    u_lower = user_text.lower()
                    is_analytical = any(k in u_lower for k in [
                        "order", "revenue", "sales", "dataset", "average",
                        "top 5", "top", "how many", "sum", "region", "analytics_orders",
                        "profit", "stats", "statistics", "unit_price", "quantity"
                    ])

                    # Exclude general conceptual questions even if they contain generic words
                    if not is_analytical or ("compare" in u_lower and "architecture" in u_lower and not any(k in u_lower for k in ["order", "revenue", "sales", "dataset", "average", "top"])):
                        return self.target_schema(
                            analysis_required=False,
                            reasoning="Query is conceptual or document-based; structured quantitative data analysis is not required.",
                        )

                    op = "count"
                    cols = None
                    group_by = None
                    limit = None
                    sort_by = None
                    sort_order = "desc"
                    tool = "analyze_dataset"
                    dataset = "orders"

                    if "query postgres" in u_lower or "analytics_orders" in u_lower:
                        tool = "query_postgres"
                        dataset = "analytics_orders"
                        cols = ["region", "revenue"]
                    elif "profit" in u_lower:
                        op = "sum"
                        cols = ["profit"]
                    elif "top" in u_lower:
                        op = "top_n"
                        limit = 5
                        sort_by = "revenue"
                        sort_order = "desc"
                        cols = ["revenue"]
                    elif "region" in u_lower or "group" in u_lower:
                        op = "group_by"
                        group_by = ["region"]
                        cols = ["revenue"]
                    elif "average" in u_lower or "mean" in u_lower:
                        op = "mean"
                        cols = ["revenue"]
                    elif "how many" in u_lower or "count" in u_lower:
                        op = "count"
                        cols = None
                    elif "stats" in u_lower or "descriptive" in u_lower:
                        op = "descriptive_stats"
                        cols = ["revenue"]
                    else:
                        op = "sum"
                        cols = ["revenue"]

                    return self.target_schema(
                        analysis_required=True,
                        reasoning=f"Structured analytical request detected. Executing {op} on dataset {dataset}.",
                        tool_name=tool,
                        dataset=dataset,
                        operation=op,
                        columns=cols,
                        group_by=group_by,
                        sort_by=sort_by,
                        sort_order=sort_order,
                        limit=limit,
                    )

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
                    findings = [
                        "Relational databases provide strong ACID consistency and strict relational schemas ideal for transactional integrity.",
                        "Document databases offer flexible schemas and horizontal partitioning suitable for high-ingestion, unstructured datasets.",
                        "Operational complexity is lower with managed relational offerings when queries require complex joins and aggregations.",
                    ]
                    if "analysis" in query_str.lower() or "revenue" in query_str.lower():
                        findings.append("Structured data analysis was executed successfully and computed exact deterministic metrics.")
                    return self.target_schema(
                        findings=findings,
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
                    has_analysis = "analysis summary:" in query_str.lower() or "data analysis" in query_str.lower()
                    has_validation_feedback = "critical validation feedback" in query_str.lower()

                    # Synthetic test scenario: incorrect revenue that corrects on retry
                    if "synthetic_incorrect_revenue" in query_str.lower():
                        if not has_validation_feedback:
                            answer_text = "Analysis completed. The total revenue is $190,000 across all orders."
                        else:
                            answer_text = "Analysis revised with verified evidence. The total revenue is $177,650 across all orders."
                        return self.target_schema(
                            request_id=kwargs.get("request_id", "mock-req-001"),
                            answer=answer_text,
                            key_points=["Revenue figure verified against approved analytical records."],
                            confidence=0.95,
                        )

                    # Synthetic test scenario: permanently invalid figure
                    if "synthetic_permanent_invalid" in query_str.lower():
                        return self.target_schema(
                            request_id=kwargs.get("request_id", "mock-req-001"),
                            answer="The total revenue is $999,999 across all orders.",
                            key_points=["Permanently unverified figure asserted."],
                            confidence=0.95,
                        )

                    # Synthetic test scenario: fabricated citation
                    if "synthetic_fabricated_citation" in query_str.lower():
                        return self.target_schema(
                            request_id=kwargs.get("request_id", "mock-req-001"),
                            answer="According to fabricated specifications, architecture details are available.",
                            key_points=["Referencing fabricated citation."],
                            confidence=0.95,
                            sources=[
                                {
                                    "document_id": "fabricated-doc-id-does-not-exist",
                                    "chunk_id": "fabricated-chunk-id-does-not-exist",
                                    "filename": "fabricated_spec.pdf",
                                    "page_number": 99,
                                    "snippet": "Fabricated content snippet.",
                                }
                            ],
                        )

                    answer_text = (
                        f"Based on the analysis of your query '{query_str[:80]}...': "
                        "PostgreSQL is strongly recommended as the default database for most SaaS startups due to "
                        "its robust ACID guarantees, rich indexing, support for JSONB, and mature ecosystem. "
                        "MongoDB is beneficial if your data model is strictly hierarchical, schema-free, "
                        "or requires rapid horizontal sharding across distributed clusters."
                    )
                    key_pts = [
                        "PostgreSQL offers superior data integrity, relational constraints, and flexible JSONB querying.",
                        "MongoDB provides rapid prototyping for polymorphic documents and out-of-the-box horizontal scaling.",
                        "For a SaaS startup, starting with PostgreSQL reduces early schema technical debt.",
                    ]
                    if has_analysis:
                        answer_text += " Furthermore, quantitative dataset analysis was successfully conducted across the approved data sources."
                        key_pts.append("Structured data analysis metrics were deterministically verified against approved datasets.")

                    return self.target_schema(
                        request_id=kwargs.get("request_id", "mock-req-001"),
                        answer=answer_text,
                        key_points=key_pts,
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
            timeout=cfg.LLM_TIMEOUT,
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
