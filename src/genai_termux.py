import os
import requests

# Get your key from https://makersuite.google.com/app/apikey
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro"  # Or "gemini-2.5-pro" if REST API supports

def gemini_chat(prompt, model=GEMINI_MODEL):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    data = r.json()
    return data['candidates'][0]['content']['parts'][0]['text']

def main():
    print("[Gemini REST] Type 'exit' to quit.")
    while True:
        user = input("You: ")
        if user.strip().lower() in ["exit", "quit"]:
            print("Exiting Gemini Termux Assistant.")
            break
        try:
            print("Gemini:", gemini_chat(user))
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("Set your GOOGLE_API_KEY in environment or .env!")
    else:
        main()
