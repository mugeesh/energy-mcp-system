# import logging
# import ollama
# from ollama import Client
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# class OllamaAPI:
#     def __init__(self, tools=None):
#         self.model = "qwen2.5:1.5b"
#         self.tools = tools or []
#         self.client = Client()
#
#     def chat(self, user_query: str):
#         messages = [
#             {
#                 "role": "system",
#                 "content": "You are a helpful energy consumption assistant. "
#                            "Use available tools to answer questions. Be concise."
#             },
#             {"role": "user", "content": user_query}
#         ]
#
#         # Use the client instance we created in __init__
#         response = self.client.chat(
#             model=self.model,
#             messages=messages,
#             tools=self.tools
#         )
#         return response
#
# if __name__ == "__main__":
#     # Example usage:
#     my_tools = [] # Add your MCP tools here
#     ollama_api = OllamaAPI(tools=my_tools)
#
#     # Simple test check
#     print("Ollama API Initialized.")
