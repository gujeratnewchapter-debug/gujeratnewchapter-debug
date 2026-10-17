"""
AI Tutor / Startup Mentor / Business Coach service layer.

Calls the OpenAI API and grounds answers in the approved knowledge base
(RFP section 10). Retrieval uses BM25-style lexical ranking over indexed
knowledge documents. A vector store can replace this implementation later
without changing the chat API or citation format.
"""
import math
import re
from collections import Counter

from django.conf import settings
from .models import KnowledgeDocument


class AIServiceUnavailable(Exception):
    """Raised when the configured AI provider cannot produce a reply."""


RETRIEVAL_STOP_WORDS = frozenset({
    'a', 'about', 'after', 'all', 'also', 'am', 'an', 'and', 'any', 'are', 'as',
    'at', 'be', 'because', 'been', 'before', 'being', 'between', 'both', 'but',
    'by', 'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each',
    'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her',
    'here', 'hers', 'him', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it',
    'its', 'just', 'me', 'more', 'most', 'my', 'no', 'nor', 'not', 'of', 'off',
    'on', 'once', 'only', 'or', 'other', 'our', 'out', 'over', 'own', 'same',
    'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their',
    'them', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to',
    'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when',
    'where', 'which', 'while', 'who', 'why', 'will', 'with', 'would', 'you',
    'your',
})


def _retrieval_tokens(text):
    return [
        token
        for token in re.findall(r'\w+', text.casefold())
        if len(token) > 1 and token not in RETRIEVAL_STOP_WORDS
    ]


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
        "You are an AI Startup and Business Advisor. Give useful, direct answers to any "
        "startup or related business question, across industries, stages, and countries. "
        "Help with ideas, customers, market research, pricing, business models, MVPs, "
        "operations, teams, legal and tax basics, business plans, financial projections, "
        "fundraising, valuation, pitch decks, marketing, growth, and strategy. Do not "
        "refuse a relevant question because it falls outside course material. Use the "
        "available context when it is relevant, and otherwise answer from your general "
        "knowledge. State assumptions and uncertainty only when they materially affect "
        "the advice; give practical next steps."
    ),
}

RESPONSE_FORMAT_RULES = (
    "\n\nResponse writing rules: Open with one or two direct, practical context sentences. "
    "Never begin with a dictionary-style definition. "
    "Use at most two heading levels; use one H1 only for a full document. "
    "Every heading must be followed by at least one complete sentence before any list. "
    "Use bullets only for genuinely parallel, scannable items, and keep nesting to one level. "
    "Do not bold the first words of list items or turn every step into a bold label followed by a colon. "
    "Use no more than one or two bold phrases in the entire response, and bold only genuine defined terms or key phrases. "
    "Group related steps under short section headings instead of producing a long numbered sequence. "
    "Include exactly one closing takeaway line, formatted only as a blockquote beginning with 'Key takeaway:' or 'Next step:'. "
    "Never repeat the closing takeaway as plain text. Be direct, concrete, and avoid unnecessary headings or nested structure."
)


def retrieve_context(query, course=None, top_k=3):
    """Rank indexed documents using BM25-style lexical relevance."""
    query_tokens = set(_retrieval_tokens(query))
    if not query_tokens or top_k <= 0:
        return '', []

    docs = KnowledgeDocument.objects.filter(is_indexed=True)
    if course:
        docs = docs.filter(course=course)

    documents = []
    for doc in docs:
        body_tokens = _retrieval_tokens(doc.raw_text)
        if not body_tokens:
            continue
        title_tokens = Counter(_retrieval_tokens(doc.title))
        documents.append((doc, Counter(body_tokens), title_tokens, len(body_tokens)))

    if not documents:
        return '', []

    document_count = len(documents)
    average_length = sum(item[3] for item in documents) / document_count
    document_frequency = Counter()
    for _, term_counts, _, _ in documents:
        document_frequency.update(term_counts.keys())

    scored = []
    for doc, term_counts, title_counts, document_length in documents:
        score = 0.0
        for term in query_tokens:
            frequency = term_counts[term]
            title_frequency = title_counts[term]
            if not frequency and not title_frequency:
                continue

            inverse_frequency = math.log(
                1 + (document_count - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            if frequency:
                length_normalizer = (
                    frequency + 1.5 * (
                        1 - 0.75 + 0.75 * document_length / average_length
                    )
                )
                score += inverse_frequency * frequency * 2.5 / length_normalizer
            if title_frequency:
                score += inverse_frequency * min(title_frequency, 2) * 1.5

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: (-item[0], item[1].id))
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
    system_prompt += RESPONSE_FORMAT_RULES
    if context_text:
        system_prompt += f"\n\nApproved knowledge base context:\n{context_text}"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    openrouter_api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')
    api_key = openrouter_api_key or openai_api_key
    if not api_key:
        raise AIServiceUnavailable(
            'The AI assistant is not configured on the server. Please contact the site administrator.'
        )

    try:
        from openai import OpenAI
        client_kwargs = {'api_key': api_key}
        if openrouter_api_key:
            client_kwargs['base_url'] = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
            client_kwargs['default_headers'] = {
                'HTTP-Referer': getattr(settings, 'AI_SITE_URL', ''),
                'X-Title': getattr(settings, 'AI_SITE_NAME', 'Ethiopian Startup School'),
            }
            model = getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        else:
            model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        client = OpenAI(**client_kwargs, timeout=45, max_retries=0)
        last_error = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=800,
                )
                reply = response.choices[0].message.content
                if not reply or not reply.strip():
                    raise ValueError('AI provider returned an empty response')
                return reply, sources
            except Exception as error:
                last_error = error
                if attempt == 0:
                    import time
                    time.sleep(0.5)
        import logging
        logging.getLogger(__name__).warning(
            'AI provider request failed after retry: %s (%s)',
            type(last_error).__name__,
            getattr(last_error, 'status_code', 'unknown status'),
        )
    except Exception as error:
        import logging
        logging.getLogger(__name__).warning('AI client setup failed: %s', type(error).__name__)
    raise AIServiceUnavailable(
        'The AI service is temporarily unavailable. Please try again shortly.'
    ) from None
