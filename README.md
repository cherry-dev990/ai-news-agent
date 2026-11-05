# 📰 AI News Agent

An AI-powered news research assistant that searches the web for relevant news articles, analyzes them using an LLM, and explains developments in a clear and structured way.

Built using Python, Streamlit, the Octen News Search API, and Groq.

## ✨ Features

- **News Search:** Search for news on any topic using the Octen API.
- **AI Relevance Verification:** Uses Groq to identify articles that directly relate to your query.
- **AI-Powered Explanation:** Generates detailed explanations based on retrieved news articles.
- **Date Filtering:** Filter news by today, last 24 hours, 3 days, 7 days, or 30 days.
- **Original Sources:** Access the original news articles.
- **Follow-up Chat:** Ask additional questions about the researched topic.
- **Search History:** Revisit recent searches during your session.
- **Download Results:** Export retrieved articles as JSON.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Web interface |
| Octen API | News search and retrieval |
| Groq API | AI analysis and explanations |
| Requests | API communication |
| JSON | Data handling and export |

## 📁 Project Structure

```text
ai-news-agent/
│
├── app.py
├── main.py
├── ai_test.py
├── requirements.txt
├── .gitignore
├── .env
└── README.md
```

**Note:** `.env` is excluded from Git because it contains API credentials.

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-news-agent.git
cd ai-news-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API keys

Create a `.env` file in the project root directory:

```env
OCTEN_API_KEY=your_octen_api_key
GROQ_API_KEY=your_groq_api_key
```

Replace the placeholders with your API keys.

### 6. Run the application

```bash
streamlit run app.py
```

The application will open in your browser.

## 🔑 API Requirements

You need API keys from:

- [Octen API](https://octen.ai/) — News search.
- [Groq](https://console.groq.com/) — AI-powered analysis.

## 🚀 Future Improvements

- Persistent database for search history.
- Improved article ranking and relevance detection.
- More advanced research capabilities.
- Support for additional news sources.
- Deployment as a publicly accessible web application.

## 👨‍💻 Author

# mr_rc_018

---

*AI News Agent — Search. Understand. Explore.*
