"""
LLM integration layer.

This module is responsible for all communication
with the language model.
"""

from openai import OpenAI
import logging
import requests
from config import MODEL_NAME, AZURE_ENDPOINT, API_KEY, OLLAMA_MODEL, MODEL_ENDPOINT
from tools.tool import Tool

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=AZURE_ENDPOINT,
            api_key=API_KEY
        )

    def _tool_to_dict(self, tool: Tool):
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
        }
    
    def _requires_complex_model(self, messages):
        """Analyzes the conversation to route to the appropriate model (Automatic Selection)."""
        if not messages:
            return True
            
        last_message = str(messages[-1].get("content", "")).lower().strip()
        simple_greetings = ["hi", "hello", "hey", "how are you", "who are you", "what is your name"]
        
        # local if the message is simple
        if last_message in simple_greetings:
            logger.info("Routing query to LOCAL OLLAMA model (Task: Simple Chat)")
            return False
            
        logger.info("Routing query to CLOUD AZURE model (Task: Complex Analysis)")
        return True

    def _generate_ollama_response(self, messages):
        """Handles requests sent to the local Ollama model."""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            }
            response = requests.post(MODEL_ENDPOINT, json=payload)
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            return {
                "message": {
                    "role": "assistant",
                    "content": content
                }
            }
        except Exception as e:
            logger.error(f"Ollama API Error: {e}", exc_info=True)
            return {"message": {"role": "assistant", "content": "Local model failed to respond."}}    
    

    def generate_response(self, messages, tools=None):
        # Route to Ollama if it's a simple task
        if not self._requires_complex_model(messages):
            return self._generate_ollama_response(messages)
        
        kwargs = {
            "model": MODEL_NAME, 
            "messages": messages
        }

        if tools:
            kwargs["tools"] = [
                self._tool_to_dict(tool)
                for tool in tools
            ]
            
        try:
            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            # EXTRACT TOKENS AND ADD TO RESULT DICT
            result = {
                "message": {
                    "role": "assistant",
                    "content": message.content
                },
                "input_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else 0,
                "output_tokens": response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 0
            }

            if getattr(message, "tool_calls", None):
                result["message"]["tool_calls"] = []
                for tc in message.tool_calls:
                    result["message"]["tool_calls"].append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

            return result
        except Exception as e:
            print(f"LLM API Error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"API Error in generate_response: {e}", exc_info=True)
            
        
        
            return {
                "message": {
                    "role": "assistant",
                    "content": "Error: Failed to generate response."
                }
            }