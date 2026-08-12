"""
AI Tutor / Startup Mentor / Business Coach service layer.

Calls the OpenAI API and grounds answers in the approved knowledge base
(RFP section 10). The retrieval step here is a simple keyword-overlap
search over `KnowledgeDocument.raw_text` — a placeholder for a real
vector database (pgvector / Chroma / Pinecone via LangChain/LlamaIndex,
per RFP section 3 AI stack). Swap `retrieve_context()` for a real
embedding-similarity search when a vector store is wired up.
"""
from django.conf import settings
from .models import KnowledgeDocument

SYSTEM_PROMPTS = {
    'tutor': (
        "You are an AI Tutor for an online startup & business education platform. "
        "Explain concepts clearly, summarize lessons, and answer student questions. "
        "Only use the provided course context; if it doesn't cover the question, say so "
        "honestly rather than guessing."
    ),
    'mentor': (
        "You are an AI Startup Mentor. Answer questions about startups, business models, "
        "fundraising, market research, pitch decks, lean startup methodology, customer "
        "discovery, and business validation. Ground answers in the provided context and "
        "cite sources when possible."
    ),
    'coach': (
        "You are an AI Business Coach. Help the student build business plans, marketing "
        "plans, financial projections, Business Model Canvas, Lean Canvas, pitch decks, "
        "SWOT/PESTEL analysis, competitor and market analysis, customer personas, and "
        "risk/investment-readiness assessments. Be structured and actionable."
    ),
}


def retrieve_context(query, course=None, top_k=3):
    """Naive keyword-overlap retrieval over indexed knowledge documents."""
    docs = KnowledgeDocument.objects.filter(is_indexed=True)
    if course:
        docs = docs.filter(course=course)

    query_words = set(query.lower().split())
    scored = []
    for doc in docs:
        text_words = set(doc.raw_text.lower().split())
        overlap = len(query_words & text_words)
        if overlap > 0:
            scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in scored[:top_k]]

    context_text = "\n\n".join(f"[Source: {d.title}]\n{d.raw_text[:1500]}" for d in top_docs)
    sources = [{'id': d.id, 'title': d.title, 'source_type': d.source_type} for d in top_docs]
    return context_text, sources


def get_ai_reply(mode, conversation_history, user_message, course=None):
    """
    conversation_history: list of {"role": "user"/"assistant", "content": str}
    Returns (reply_text, sources)
    """
    context_text, sources = retrieve_context(user_message, course=course)

    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['tutor'])
    if context_text:
        system_prompt += f"\n\nApproved knowledge base context:\n{context_text}"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    if not settings.OPENAI_API_KEY:
        # Dev-mode fallback so the app runs without an API key configured
        return (
            "[AI Tutor - dev mode: set OPENAI_API_KEY to enable real responses] "
            f"I received your question: '{user_message}'.",
            sources,
        )

    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=messages,
        max_tokens=800,
    )
    reply = response.choices[0].message.content
    return reply, sources
