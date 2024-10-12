import json

# Load and format large JSON file
with open('data/ChatGPT-2024-10-12-10-05-59/conversations.json', 'r') as f:
    data = json.load(f)

# Write formatted JSON to a new file
with open('data/ChatGPT-2024-10-12-10-05-59/conversations_formatted.json', 'w') as f:
    json.dump(data, f, indent=4)

print("JSON file formatted successfully.")
