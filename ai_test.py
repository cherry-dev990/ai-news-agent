import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "system",
            "content": "You are an expert technology news analyst."
        },
        {
            "role": "user",
            "content": "Explain what an LLM is in simple English."
        }
    ],
    max_completion_tokens=300
)

print("\nAI RESPONSE:\n")
print(response.choices[0].message.content)