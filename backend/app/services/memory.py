import json
import logging
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.config import get_settings
from app.database import get_connection

logger = logging.getLogger(__name__)

MEMORY_EXTRACTION_PROMPT = """Analyze this conversation exchange and extract any new facts about the user that would be useful to remember across future conversations.

User message: {user_message}
Assistant response: {assistant_response}

Extract facts in these categories:
- general: name, age, occupation
- preference: likes, dislikes, preferred tools/languages
- project: what they're working on, tech stack
- technical: skills, experience level
- personal: location, timezone, interests

Return a JSON array of objects with "content" and "category" fields.
Return an empty array if there are no new facts worth storing.

Rules:
- Only store facts explicitly stated or strongly implied by the user
- Do not store trivial facts (greetings, single-word responses)
- Do not store opinions the assistant expressed
- Keep each fact to one concise sentence
- Maximum 3 facts per exchange"""


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


async def recall_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    try:
        embedding = await embed_text(query)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        async with get_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT content, category,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM user_memories
                WHERE user_id = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                embedding_str, user_id, limit,
            )

        return [
            row["content"] for row in rows
            if row["similarity"] > 0.3
        ]
    except Exception:
        logger.exception("Failed to recall memories")
        return []


async def is_duplicate_memory(user_id: str, content: str, threshold: float = 0.9) -> bool:
    embedding = await embed_text(content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 - (embedding <=> $1::vector) AS similarity
            FROM user_memories
            WHERE user_id = $2
            ORDER BY embedding <=> $1::vector
            LIMIT 1
            """,
            embedding_str, user_id,
        )

    return row is not None and row["similarity"] > threshold


async def extract_and_store_memories(
    user_id: str,
    user_message: str,
    assistant_response: str,
) -> list[dict]:
    if not assistant_response.strip():
        return []

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        extraction = await llm.ainvoke([
            SystemMessage(content=MEMORY_EXTRACTION_PROMPT.format(
                user_message=user_message,
                assistant_response=assistant_response,
            ))
        ])

        try:
            new_facts = json.loads(extraction.content)
        except json.JSONDecodeError:
            return []

        if not isinstance(new_facts, list):
            return []

        stored = []
        for fact in new_facts[:3]:
            content = fact.get("content", "")
            category = fact.get("category", "general")

            if not content or len(content) > 500:
                continue

            if await is_duplicate_memory(user_id, content):
                continue

            embedding = await embed_text(content)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            async with get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_memories (user_id, content, category, embedding)
                    VALUES ($1, $2, $3, $4::vector)
                    """,
                    user_id, content, category, embedding_str,
                )

            stored.append(fact)

        return stored
    except Exception:
        logger.exception("Failed to extract/store memories")
        return []
