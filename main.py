import os
import json
import requests

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
GROQ_MODEL = "openai/gpt-oss-20b"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

DATA_FILE = "daily_news.json"

current_articles = []


# ==========================================
# 1. DATE FILTERING
# ==========================================

def select_date_range():

    print("\nSelect date range:")
    print("1. Today")
    print("2. Last 24 hours")
    print("3. Last 3 days")
    print("4. Last 7 days")
    print("5. Last 30 days")

    choice = input("\nEnter choice: ").strip()

    options = {
        "1": ("day", "today"),
        "2": ("day", "24h"),
        "3": ("week", "3d"),
        "4": ("week", "7d"),
        "5": ("month", "30d")
    }

    return options.get(choice, ("week", "7d"))


def filter_by_date(articles, period):

    now = datetime.now().astimezone()

    if period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

    elif period == "24h":
        cutoff = now - timedelta(hours=24)

    elif period == "3d":
        cutoff = now - timedelta(days=3)

    elif period == "7d":
        cutoff = now - timedelta(days=7)

    else:
        cutoff = now - timedelta(days=30)

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

        except ValueError:
            continue

    return filtered


# ==========================================
# 2. NEWS SEARCH
# ==========================================

def search_news(topic, date_range):

    headers = {
        "Content-Type": "application/json",
        "x-api-key": OCTEN_API_KEY
    }

    payload = {
        "query": topic,
        "count": 10,
        "time_range": date_range
    }

    print("\nSearching for latest news...")

    response = requests.post(
        OCTEN_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != 0:
        raise ValueError(data.get("msg", "News API returned an error"))

    articles = data.get("data", {}).get("results", [])

    return articles


# ==========================================
# 3. NEWS DISPLAY
# ==========================================

def display_news(articles):

    global current_articles

    current_articles = articles

    if not articles:
        print("\nNo news found for the selected date range.")
        return

    print("\n" + "=" * 65)
    print("                 LATEST NEWS")
    print("=" * 65)

    for i, article in enumerate(articles, start=1):

        print(f"\n{i}. {article.get('title', 'No title')}")

        print("Published:", article.get("time_published", "Unknown"))

        print("\nDescription:")

        print(
            article.get("highlight", "No description available.")[:400]
        )

        print("\nSource:", article.get("url", "Unavailable"))

        print("-" * 65)


# ==========================================
# 4. AI EXPLANATION + CATEGORISATION
# ==========================================

def ai_analyze_news(articles):

    if not groq_client:
        print("\nGroq API key not configured.")
        return

    if not articles:
        return

    news_context = ""

    for i, article in enumerate(articles, start=1):

        news_context += f"""
Article {i}:
Title: {article.get('title')}
Description: {article.get('highlight', '')[:700]}
Published: {article.get('time_published')}
"""

    prompt = f"""
You are an expert technology and world news analyst.

Analyse the following news articles.

For EACH article:

1. Give a category.
   Examples: Technology, AI, Business, Politics, Science, Sports.

2. Assign importance:
   HIGH, MEDIUM or LOW.

3. Explain the news in simple English.

4. Explain why this news matters.

5. Give one real-world example if useful.

6. Rank all articles from most important to least important.

Be accurate. Do not invent facts.

NEWS ARTICLES:

{news_context}
"""

    print("\nAI is analysing the news...\n")

    try:

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a reliable news analyst."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_completion_tokens=1800
        )

        analysis = response.choices[0].message.content

        print("\n" + "=" * 65)
        print("             AI NEWS ANALYSIS")
        print("=" * 65)

        print(analysis)

        return analysis

    except Exception as error:

        print("\nAI analysis failed:", error)
        return None


# ==========================================
# 5. FOLLOW-UP QUESTIONS
# ==========================================

def ask_followup(articles):

    if not groq_client:
        print("\nGroq API key not configured.")
        return

    if not articles:
        print("\nSearch for news first.")
        return

    context = ""

    for i, article in enumerate(articles, start=1):

        context += f"""
Article {i}:
Title: {article.get('title')}
Description: {article.get('highlight', '')[:700]}
"""

    conversation = [
        {
            "role": "system",
            "content": f"""
You are an AI news assistant.

Answer questions using the following retrieved news.

If the information is not available in the articles,
clearly say so instead of inventing information.

NEWS CONTEXT:
{context}
"""
        }
    ]

    print("\nYou can now ask questions about these articles.")
    print("Type 'exit' to return to the main menu.")

    while True:

        question = input("\nYour question: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        conversation.append({
            "role": "user",
            "content": question
        })

        try:

            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=conversation,
                max_completion_tokens=700
            )

            answer = response.choices[0].message.content

            print("\nAI:", answer)

            conversation.append({
                "role": "assistant",
                "content": answer
            })

        except Exception as error:

            print("AI error:", error)
            conversation.pop()


# ==========================================
# 6. DAILY NEWS AGENT
# ==========================================

def save_daily_news(topic, articles, analysis):

    record = {
        "topic": topic,
        "generated_at": datetime.now().astimezone().isoformat(),
        "articles": articles,
        "ai_analysis": analysis
    }

    if os.path.exists(DATA_FILE):

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                records = json.load(file)

        except (json.JSONDecodeError, OSError):
            records = []

    else:
        records = []

    records.append(record)

    with open(DATA_FILE, "w", encoding="utf-8") as file:

        json.dump(records, file, indent=4, ensure_ascii=False)

    print("\nDaily news saved to:", DATA_FILE)


def run_daily_agent(topics):

    print("\n" + "=" * 65)
    print("             DAILY NEWS AGENT")
    print("=" * 65)

    for topic in topics:

        try:

            print(f"\nSearching daily updates for: {topic}")

            articles = search_news(topic, "day")

            articles = filter_by_date(articles, "24h")

            if not articles:
                print("No recent news found.")
                continue

            display_news(articles)

            analysis = ai_analyze_news(articles)

            save_daily_news(topic, articles, analysis)

        except Exception as error:

            print(f"Daily agent failed for {topic}: {error}")


def schedule_daily_agent():

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler

    except ImportError:
        print("\nInstall APScheduler: pip install apscheduler")
        return

    topics_input = input(
        "\nEnter topics separated by commas: "
    ).strip()

    if not topics_input:
        print("No topics entered.")
        return

    topics = [
        topic.strip()
        for topic in topics_input.split(",")
        if topic.strip()
    ]

    schedule_time = input(
        "\nEnter daily time (HH:MM, 24-hour format): "
    ).strip()

    try:

        hour, minute = map(int, schedule_time.split(":"))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

    except ValueError:

        print("Invalid time. Example: 08:30")
        return

    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_daily_agent,
        "cron",
        hour=hour,
        minute=minute,
        args=[topics]
    )

    print("\nDaily agent scheduled successfully!")
    print("Topics:", topics)
    print(f"Schedule: Every day at {schedule_time}")
    print("\nKeep this program running for automatic execution.")
    print("Press CTRL+C to stop.")

    try:
        scheduler.start()

    except KeyboardInterrupt:
        print("\nDaily agent stopped.")


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():

    if not OCTEN_API_KEY:
        print("Error: OCTEN_API_KEY missing in .env")
        return

    print("\n" + "=" * 65)
    print("                  AI NEWS AGENT")
    print("=" * 65)

    while True:

        print("\nMAIN MENU")
        print("1. Search news")
        print("2. AI explain and analyse news")
        print("3. Ask follow-up questions")
        print("4. Start daily news agent")
        print("5. Exit")

        choice = input("\nSelect an option: ").strip()

        # SEARCH NEWS
        if choice == "1":

            topic = input("\nEnter a topic: ").strip()

            if not topic:
                print("Enter a valid topic.")
                continue

            api_range, exact_period = select_date_range()

            try:

                articles = search_news(topic, api_range)

                articles = filter_by_date(
                    articles,
                    exact_period
                )

                display_news(articles)

                if articles:

                    print("\n1. Analyse these articles with AI")
                    print("2. Ask follow-up questions")
                    print("3. Return to menu")

                    action = input("\nChoose: ").strip()

                    if action == "1":

                        ai_analyze_news(articles)

                    elif action == "2":

                        ask_followup(articles)

            except requests.RequestException as error:

                print("\nNews API error:", error)

            except (ValueError, KeyError) as error:

                print("\nError:", error)

        # AI ANALYSIS
        elif choice == "2":

            if current_articles:
                ai_analyze_news(current_articles)

            else:
                print("\nSearch for news first.")

        # FOLLOW-UP
        elif choice == "3":

            ask_followup(current_articles)

        # DAILY AGENT
        elif choice == "4":

            schedule_daily_agent()

        # EXIT
        elif choice == "5":

            print("\nThank you for using AI News Agent!")
            break

        else:

            print("\nInvalid choice. Try again.")


if __name__ == "__main__":
    main()