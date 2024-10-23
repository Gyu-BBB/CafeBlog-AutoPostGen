import os
import openai

api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

completion = client.chat.completions.create(
    model="solar-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "한국말로 인사해줘"
        }
    ]
)

print(completion.choices[0].message.content)

