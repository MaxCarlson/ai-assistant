import argparse
import threading
from queue import Queue
from src.ui import start_chat_loop, console, format_and_print_thought
from src.agent_manager import AgentManager
from src import task_manager
import re

class CLIAgent:
    def __init__(self, agent_manager: AgentManager, task_id: str, agent_mode: bool = False):
        self.agent_manager = agent_manager
        self.task_id = task_id
        self.agent_mode = agent_mode
        self.notification_queue = Queue()

    def handle_task(self, user_input: str, conversation_history: list) -> str:
        if self.agent_mode:
            task = task_manager.get_task(self.task_id)
            if not task:
                return {"thought": "Error", "response": f"Task {self.task_id} not found."}

            task_manager.update_task_goal(self.task_id, user_input)
            agent_thread = threading.Thread(target=self.agent_manager.start_task, args=(task, self.notification_queue))
            agent_thread.start()

            while agent_thread.is_alive() or not self.notification_queue.empty():
                while not self.notification_queue.empty():
                    notification = self.notification_queue.get()
                    if "AI Thought:" in notification:
                        thought_text = notification.replace("AI Thought:", "").strip()
                        format_and_print_thought(thought_text)
                    elif "Tool" in notification:
                        console.print(f"[cyan]{notification}[/cyan]")
                    else:
                        console.print(f"[green]{notification}[/green]")
            
            agent_thread.join()

            final_task_state = task_manager.get_task(self.task_id)
            history = final_task_state.get("history", [])
            
            final_response = "No response from agent."
            for i in reversed(history):
                if "Observation: Task marked as complete" in i:
                    final_response = i.replace("Observation: ", "")
                    break
                elif "Observation: " in i:
                    final_response = i.replace("Observation: ", "")
                    break
            
            return {"thought": "Done", "response": final_response}
        else:
            return self.agent_manager.get_direct_response(user_input, conversation_history)

def run_cli():
    parser = argparse.ArgumentParser(description="AI Assistant CLI")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="The model to use for the agent.")
    parser.add_argument("--sandbox", action="store_true", help="Enable sandbox mode.")
    parser.add_argument("--agent", action="store_true", help="Run in agent mode.")
    args = parser.parse_args()

    try:
        agent_manager = AgentManager(model_name=args.model, debug=args.debug, sandbox=args.sandbox)
        task_id = task_manager.create_task("Chat with user.")
        conversational_agent = CLIAgent(agent_manager=agent_manager, task_id=task_id, agent_mode=args.agent)
        start_chat_loop(agent=conversational_agent, agent_manager=agent_manager, debug=args.debug)
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")