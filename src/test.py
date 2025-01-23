import os
import google.generativeai as genai

# Configure the API using the environment variable
api_key = os.getenv('GOOGLE_API_KEY_AI_ASSISTANT')
genai.configure(api_key=api_key)

def chat():
    model = genai.GenerativeModel("gemini-1.5-flash-8b")
    chat_session = model.start_chat(history=[])
    print("Chatbot is ready. Type 'quit' to exit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break

        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=200,
            temperature=1.0,
        )

        # Send message to the chat and get response
        response = chat_session.send_message(user_input, stream=True, generation_config=generation_config)

        # Handle streaming output
        print("Bot:", end=" ")
        try:
            for part in response:
                print(part.text, end="")
        except TypeError:
            # If the response is not iterable, print it directly
            print(response.text)
        print()  # Ensure the next prompt appears on a new line

if __name__ == "__main__":
    chat()
