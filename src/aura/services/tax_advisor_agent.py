from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from sqlalchemy import text
from aura.core.config import settings
from aura.db.session import AsyncSessionFactory

@tool
async def search_tax_rules(question: str) -> str:
    """Search verified tax-rule chunks before answering a tax-rule question."""
    sql = text("SELECT source_name, content FROM tax_rule_chunks WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :question) ORDER BY created_at DESC LIMIT 4")
    async with AsyncSessionFactory() as session:
        rows = (await session.execute(sql, {"question": question})).all()
    return "\n\n".join(f"Source: {row.source_name}\n{row.content}" for row in rows) if rows else "No verified tax-rule source was found."

@tool
async def get_document_status(user_id: str) -> str:
    """Get only the requesting user's uploaded-document processing statuses."""
    sql = text("SELECT filename, processing_status FROM documents WHERE user_id = CAST(:user_id AS uuid) ORDER BY created_at DESC LIMIT 20")
    async with AsyncSessionFactory() as session:
        rows = (await session.execute(sql, {"user_id": user_id})).all()
    return "\n".join(f"{row.filename}: {row.processing_status}" for row in rows) if rows else "No uploaded documents were found."

def build_tax_advisor():
    model = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0)
    return create_react_agent(model, tools=[search_tax_rules, get_document_status], prompt="You are TaxAura's tax assistant. Use tools for facts. Never invent tax rules, tax amounts, deductions, or deadlines. State source names when a rule was retrieved.")

async def answer_question(user_id: str, question: str) -> str:
    result = await build_tax_advisor().ainvoke({"messages": [("user", f"User ID: {user_id}\nQuestion: {question}")]})
    return result["messages"][-1].content
