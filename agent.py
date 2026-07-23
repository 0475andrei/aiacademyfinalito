import json
import logging


logger = logging.getLogger(__name__)

"""Core agent orchestration.
The agent coordinates communication between
the conversation context and the language model."""

class Agent:
    def __init__(self, llm_client, context, tools=None):
        self.llm_client = llm_client
        self.context = context
        self.tools = {tool.name: tool for tool in tools} if tools else {}

    def _handle_tool_calls(self, tool_calls):
        results = []
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_id = tc["id"]
            
            # Logging tool execution
            logger.info(f"Executing Tool Call: {tool_name}")
            
            try:
                # Attempt to parse arguments
                arguments_str = tc["function"]["arguments"]
                arguments = json.loads(arguments_str) if arguments_str else {}
                
                # Find and execute tool
                tool = self.tools.get(tool_name)
                if tool:
                    raw_result = tool.callback(**arguments)
                    result = str(raw_result) if raw_result is not None else "Tool executed successfully (no output)."
                else:
                    # Logging errors
                    logger.error(f"Tool '{tool_name}' not defined in registry.")
                    result = f"Error: Tool '{tool_name}' is not currently available."
            
            except json.JSONDecodeError:
                # Logging warnings
                logger.warning(f"Invalid JSON arguments for '{tool_name}'")
                result = "Error: Invalid JSON arguments"
            except Exception as e:
                # Logging errors with exception traceback
                logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                result = f"Error: Tool execution failed: {str(e)}"

            results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": str(result)
            })
        return results

    def process_message(self, user_message):
        
        # Logging user input
        logger.info(f"User Input: {user_message}")
        
        self.context.add_message({
            "role": "user",
            "content": user_message
        })

        response = self.llm_client.generate_response(
            self.context.get_history(),
            tools=list(self.tools.values())
        )
        
       
        if response:
            self.context.input_tokens += response.get("input_tokens", 0)
            self.context.output_tokens += response.get("output_tokens", 0)
        
        
        if response and "message" in response:
            message = response["message"]
        else:
            message = {
                "role": "assistant", 
                "content": "I apologize, but I failed to receive a response from the model."
            }

        tool_calls = message.get("tool_calls", [])
        tool_used = None 

        if tool_calls:
            self.context.add_message(message)
            tool_used = tool_calls[0]["function"]["name"] 
            
           
            for tc in tool_calls:
                logger.info(f"System: Triggering tool '{tc['function']['name']}'...")

            tool_results = self._handle_tool_calls(tool_calls)
            
            for result in tool_results:
                if not result.get("content") or result["content"] == "[]":
                    result["content"] = "No relevant information could be retrieved for this query."
                self.context.add_message(result)

            response = self.llm_client.generate_response(
                self.context.get_history()
            )
            
            if response and "message" in response:
                message = response["message"]

        # --- FALLBACK: Handle Empty LLM Response ---
        if not message.get("content"):
            message["content"] = "I'm sorry, I couldn't find a direct answer to your question. Please contact the IT Service Desk for further assistance."
        
        # Logging model response
        logger.info(f"Model Response: {message.get('content', '')}")
        self.context.add_message(message)
        
        return message.get("content", ""), tool_used