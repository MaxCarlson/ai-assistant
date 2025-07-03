import argparse
import threading
from queue import Queue
from src.ui import start_chat_loop, console, format_and_print_thought
from src.agent_manager import AgentManager
from src import task_manager
import re

class CLIAgent:
    def __init__(self, agent_manager: AgentManager, task_id: str):
        self.agent_manager = agent_manager
        self.task_id = task_id
        self.notification_queue = Queue()

    def handle_task(self, user_input: str, conversation_history: list) -> str:
        task = task_manager.get_task(self.task_id)
        if not task:
            return {"thought": "Error", "response": f"Task {self.task_id} not found."}

        # Update the goal of the task with the latest user input
        task_manager.update_task_goal(self.task_id, user_input)

        # Run the agent in a separate thread to avoid blocking the UI
        agent_thread = threading.Thread(target=self.agent_manager.start_task, args=(task, self.notification_queue))
        agent_thread.start()

        # Process notifications from the agent
        while agent_thread.is_alive() or not self.notification_queue.empty():
            while not self.notification_queue.empty():
                notification = self.notification_queue.get()
                # This is a simple way to show agent activity.
                # A more sophisticated UI could parse these messages.
                if "AI Thought:" in notification:
                    thought_text = notification.replace("AI Thought:", "").strip()
                    format_and_print_thought(thought_text)
                elif "Tool" in notification:
                    console.print(f"[cyan]{notification}[/cyan]")
                else:
                    console.print(f"[green]{notification}[/green]")
        
        agent_thread.join()

        # Return the final result
        final_task_state = task_manager.get_task(self.task_id)
        history = final_task_state.get("history", [])
        
        # Find the last observation which contains the final result
        final_response = "No response from agent."
        for i in reversed(history):
            if "Observation: Task marked as complete" in i:
                final_response = i.replace("Observation: ", "")
                break
            elif "Observation: " in i:
                final_response = i.replace("Observation: ", "")
                break
        
        return {"thought": "Done", "response": final_response}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Assistant CLI for Termux")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--model", type=str, default="gemini-1.5-pro-latest", help="The model to use for the agent.")
    args = parser.parse_args()

    try:
        # Initialize managers
        agent_manager = AgentManager(model_name=args.model, debug=args.debug)

        # Create a new task for the session
        task_id = task_manager.create_task("Chat with user in Termux.")
        
        # Initialize the agent
        conversational_agent = CLIAgent(agent_manager=agent_manager, task_id=task_id)
        
        # Start the chat loop
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager, debug=args.debug)

    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
