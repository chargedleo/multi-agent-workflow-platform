"""CLI script to rebuild the FAISS vector index from PostgreSQL document records."""

import asyncio
from backend.app.core.logging import get_logger, setup_logging
from backend.app.db.session import close_database_connection, get_db_context
from backend.app.documents.service import DocumentService

logger = get_logger("rebuild_index")


async def main() -> None:
    """Run index rebuild workflow."""
    setup_logging("INFO")
    logger.info("Starting FAISS vector index rebuild from PostgreSQL...")
    async with get_db_context() as session:
        stats = await DocumentService.rebuild_vector_index(session)

    print("\n" + "=" * 50)
    print("FAISS Index Rebuild Complete")
    print("=" * 50)
    print(f"Documents Processed: {stats['documents_processed']}")
    print(f"Chunks Processed:    {stats['chunks_processed']}")
    print(f"Vectors Generated:   {stats['vectors_generated']}")
    print(f"Final Index Size:    {stats['final_index_size']}")
    print("=" * 50 + "\n")

    await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())
