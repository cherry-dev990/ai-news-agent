import os
import json
import requests
import streamlit as st

from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

OCTEN_API_KEY = os.getenv("OCTEN_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OCTEN_URL = "https://api.octen.ai/news-search"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


st.set_page_config(
    page_title="AI News Agent",
    page_icon="📰",
    layout="wide"
)


# ==========================================
# SESSION STATE
# ==========================================

if "articles" not in st.session_state:
    st.session_state.articles = []

if "explanation" not in st.session_state:
    st.session_state.explanation = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""


# ==========================================
# HEADER
# ==========================================

st.title("📰 AI News Agent")

st.markdown(
    "### Understand what's happening in the world."
)

st.caption(
    "Search a topic, get an AI-powered explanation "
    "and explore the original news articles."
)


# ==========================================
# DATE FILTER
# ==========================================

st.sidebar.header("Search Settings")

enable_date_filter = st.sidebar.checkbox(
    "Enable date filter",
    value=False
)

date_period = None

if enable_date_filter:

    date_period = st.sidebar.selectbox(
        "Select date range",
        [
            "Today",
            "Last 24 hours",
            "Last 3 days",
            "Last 7 days",
            "Last 30 days"
        ]
    )


api_ranges = {
    "Today": "day",
    "Last 24 hours": "day",
    "Last 3 days": "week",
    "Last 7 days": "week",
    "Last 30 days": "month"
}


# ==========================================
# DATE FILTER FUNCTION
# ==========================================

def filter_by_date(articles, period):

    now = datetime.now().astimezone()

    durations = {
        "Today": timedelta(
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
        ) + timedelta(days=0),

        "Last 24 hours": timedelta(hours=24),

        "Last 3 days": timedelta(days=3),

        "Last 7 days": timedelta(days=7),

        "Last 30 days": timedelta(days=30)
    }

    cutoff = now - durations[period]

    filtered = []

    for article in articles:

        published = article.get("time_published")

        if not published:
            continue

        try:

            published_date = datetime.fromisoformat(
                published.replace("Z", "+00:00")
            ).astimezone()

            if published_date >= cutoff:
                filtered.append(article)

        except (ValueError, TypeError):
            continue

    return filtered


# ==========================================
# NEWS SEARCH
# ==========================================

def search_news(topic, date_range=None):

    headers = {
        "Content-Type": "application/json",
        "x-api-key": OCTEN_API_KEY
    }

    payload = {
        "query": topic,
        "count": 10
    }

    # Only send date restriction when user enables it
    if date_range:
        payload["time_range"] = date_range

    response = requests.post(
        OCTEN_URL,
        headers=headers,
        json=payload,
        timeout=40
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:

        raise Exception(
            data.get("msg", "News API error")
        )

    return data.get(
        "data", {}
    ).get(
        "results", []
    )


# ==========================================
# AI RELEVANCE FILTER
# ==========================================

def filter_relevant_news(topic, articles):

    if not articles:
        return []

    article_data = []

    for i, article in enumerate(articles):

        article_data.append({
            "id": i,
            "title": article.get("title", ""),
            "summary": article.get("highlight", "")
        })

    prompt = f"""
You are a precise news relevance evaluator.

USER QUERY:
{topic}

TASK:

Evaluate the following news articles.

Select ONLY articles that directly answer or meaningfully
contribute to answering the user's exact query.

IMPORTANT:

- Do not select articles just because they mention a similar
  company, person, technology or industry.
- Distinguish between related topics and the exact event.
- If the query asks about an acquisition, do not select
  general company news.
- If the query asks about a specific product, do not select
  unrelated product announcements.
- Related background information can be included only when
  it genuinely helps answer the query.
- Do not invent relevance.
- If no article is relevant, return an empty list.

Return ONLY valid JSON in this format:

{{
    "relevant_ids": [0, 2, 4]
}}

ARTICLES:

{json.dumps(article_data, indent=2)}
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_completion_tokens=500
    )

    result = response.choices[0].message.content.strip()

    try:

        # Handle possible markdown code fences
        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

        parsed = json.loads(result)

        relevant_ids = parsed.get("relevant_ids", [])

        relevant_ids = [
            i for i in relevant_ids
            if isinstance(i, int) and 0 <= i < len(articles)
        ]

        return [
            articles[i]
            for i in relevant_ids
        ]

    except (json.JSONDecodeError, TypeError, AttributeError):

        # If AI relevance filtering fails, preserve original results
        return articles


# ==========================================
# AI EXPLANATION
# ==========================================

def generate_explanation(topic, articles):

    context = ""

    for i, article in enumerate(articles, 1):

        context += f"""

ARTICLE {i}

Title:
{article.get('title', '')}

Summary:
{article.get('highlight', '')}

Publication Date:
{article.get('time_published', '')}

"""

    prompt = f"""
You are an advanced AI news research assistant.

The user has asked:

"{topic}"

Your job is to provide a precise, detailed and informative
answer to the user's exact query.

Use the retrieved news information as your primary evidence.

HOW TO WRITE THE ANSWER:

1. DIRECT ANSWER

Start by answering exactly what the user asked.

Do not begin with generic introductions or unnecessary
definitions.

2. COMPLETE EXPLANATION

Explain the actual development in detail.

Include relevant information such as:

- What happened?
- Who is involved?
- When did it happen?
- Why did it happen?
- How did it happen?
- What are the important details?
- What makes this development significant?

Include only details relevant to the query.

3. CONTEXT AND IMPACT

Explain the implications of the development.

Discuss its impact on the companies, technology, industry
or people involved, wherever supported by the information.

4. FINAL TAKEAWAY

End with a concise conclusion that captures the most
important point.

STRICT RULES:

- Answer the exact query, not a broader related topic.
- Do not explain everything from scratch.
- Do not write a generic AI-generated news summary.
- Be informative, precise and detailed.
- Write in natural paragraphs with useful headings.
- Tell the story of the actual development when appropriate.
- Do not include article URLs or hyperlinks.
- Do not include source numbers like [1], [2], etc.
- Do not fabricate dates, amounts, acquisitions or statements.
- Do not present rumours as confirmed facts.
- Clearly distinguish confirmed information from reports
  or speculation.
- If the available articles do not contain enough information
  to answer the query, explicitly mention that limitation.
- Do not pretend to have verified information that is absent
  from the retrieved articles.

NEWS INFORMATION:

{context}
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_completion_tokens=2500
    )

    return response.choices[0].message.content


# ==========================================
# FOLLOW-UP QUESTIONS
# ==========================================

def ask_ai(question):

    context = ""

    for article in st.session_state.articles:

        context += f"""
Title: {article.get('title', '')}

Summary: {article.get('highlight', '')}

Date: {article.get('time_published', '')}

"""

    messages = [

        {
            "role": "system",
            "content": f"""
You are an AI news research assistant.

The user's original query was:

{st.session_state.current_topic}

Here is the retrieved news information:

{context}

Previous AI explanation:

{st.session_state.explanation}

Answer follow-up questions accurately and clearly.

Use the available information as evidence.

Do not invent facts.

If the information is unavailable, say so.
"""
        }

    ]

    messages.extend(
        st.session_state.messages
    )

    messages.append({
        "role": "user",
        "content": question
    })

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        max_completion_tokens=1000
    )

    answer = response.choices[0].message.content

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    return answer


# ==========================================
# SEARCH SECTION
# ==========================================

st.divider()

st.subheader("🔍 Search for anything")

topic = st.text_input(
    "Enter your query",
    placeholder="Example: Nvidia buying Groq LPU"
)

search_button = st.button(
    "Search and Explain",
    type="primary"
)


# ==========================================
# SEARCH EXECUTION
# ==========================================

if search_button:

    if not OCTEN_API_KEY:

        st.error("OCTEN_API_KEY is missing.")

    elif not GROQ_API_KEY:

        st.error("GROQ_API_KEY is missing.")

    elif not topic.strip():

        st.warning("Please enter a search query.")

    else:

        try:

            st.session_state.articles = []
            st.session_state.explanation = ""
            st.session_state.messages = []
            st.session_state.current_topic = topic

            # STEP 1: SEARCH
            with st.spinner("Searching for news articles..."):

                api_range = (
                    api_ranges[date_period]
                    if enable_date_filter
                    else None
                )

                articles = search_news(
                    topic,
                    api_range
                )

            if not articles:

                st.warning(
                    "No articles were found for this query."
                )

            else:

                # STEP 2: RELEVANCE FILTER
                with st.spinner(
                    "Checking which articles match your query..."
                ):

                    relevant_articles = filter_relevant_news(
                        topic,
                        articles
                    )

                if not relevant_articles:

                    st.warning(
                        "The search returned articles, "
                        "but none matched your query closely enough. "
                        "Try rephrasing your search."
                    )

                else:

                    # STEP 3: DATE FILTER
                    if enable_date_filter:

                        relevant_articles = filter_by_date(
                            relevant_articles,
                            date_period
                        )

                    if not relevant_articles:

                        st.warning(
                            "No matching articles were found "
                            "within the selected date range."
                        )

                    else:

                        st.session_state.articles = relevant_articles

                        # STEP 4: GENERATE EXPLANATION
                        with st.spinner(
                            "AI is analysing the news and preparing "
                            "your explanation..."
                        ):

                            explanation = generate_explanation(
                                topic,
                                relevant_articles
                            )

                            st.session_state.explanation = explanation

                        st.success(
                            f"Research completed! "
                            f"{len(relevant_articles)} relevant "
                            f"articles found."
                        )

        except requests.exceptions.RequestException as e:

            st.error(
                f"News API connection error: {e}"
            )

        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )


# ==========================================
# AI EXPLANATION DISPLAY
# ==========================================

if st.session_state.explanation:

    st.divider()

    st.header("🧠 AI Explanation")

    st.markdown(
        st.session_state.explanation
    )


# ==========================================
# ORIGINAL NEWS ARTICLES
# ==========================================

if st.session_state.articles:

    st.divider()

    st.header("📰 Original News Articles")

    st.caption(
        "Explore the original articles retrieved for your query."
    )

    for i, article in enumerate(
        st.session_state.articles,
        1
    ):

        with st.container(border=True):

            # Original title
            st.markdown(
                f"### {i}. {article.get('title', 'Untitled')}"
            )

            # Original summary
            if article.get("highlight"):

                st.write(
                    article.get("highlight")
                )

            # Original publication date
            st.caption(
                f"Published: "
                f"{article.get('time_published', 'Unknown')}"
            )

            # Original article link
            url = article.get("url")

            if url:

                st.link_button(
                    "Read Original Article",
                    url
                )


    # DOWNLOAD NEWS
    st.download_button(
        "⬇️ Download News JSON",

        data=json.dumps(
            st.session_state.articles,
            indent=4
        ),

        file_name="news_digest.json",

        mime="application/json"
    )


# ==========================================
# FOLLOW-UP CHAT
# ==========================================

if st.session_state.articles:

    st.divider()

    st.header("💬 Ask Follow-up Questions")

    st.caption(
        "Continue exploring the topic with AI."
    )

    # Previous conversation
    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(
                message["content"]
            )

    # New question
    question = st.chat_input(
        "Ask anything about this topic..."
    )

    if question:

        if not groq_client:

            st.error("GROQ_API_KEY is missing.")

        else:

            with st.spinner("Thinking..."):

                try:

                    ask_ai(question)

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"AI response error: {e}"
                    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "AI News Agent | Powered by Octen API and Groq"
)