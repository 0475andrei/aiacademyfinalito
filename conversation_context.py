import json
import logging
from summarizer import summarize_context
from config import OLLAMA_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class ConversationContext:
    def __init__(self, max_tokens=3000):
        self.history = []
        self.max_tokens = max_tokens
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.input_tokens = 0
        self.output_tokens = 0

    def add_message(self, message):
        self.history.append(message)
        self._manage_context_size()

    def get_history(self):
        return self.history

    def _manage_context_size(self):
        # Declanșăm sumarizarea dacă istoricul depășește o anumită limită
        MAX_MESSAGES = 10
        
        if len(self.history) > MAX_MESSAGES:
            logger.info("Context prea lung. Începem sumarizarea cu Ollama...")
            system_prompt = self.history[0]
            recent_messages = self.history[-4:]
            messages_to_summarize = self.history[1:-4]
            
            
            mesaje_procesate = []
            for m in messages_to_summarize:
                if isinstance(m, dict): # Ne asigurăm că e dicționar, nu string
                    role = m.get('role', 'unknown').upper()
                    content = m.get('content', '')
                    mesaje_procesate.append(f"{role}: {content}")
                else:
                    mesaje_procesate.append(f"SYSTEM: {str(m)}")
                    
            text_to_summarize = "\n".join(mesaje_procesate)
            
            try:
               
                summary_text = summarize_context(text_to_summarize)
                
                
                summary_message = {
                    "role": "system",
                    "content": f"[MEMORIE COMPRESATĂ A CONVERSAȚIEI]: {summary_text}"
                }
                
                
                self.history = [system_prompt, summary_message] + recent_messages
                logger.info("Context sumarizat și curățat cu succes!")
                
            except Exception as e:
                logger.error(f"Eroare la sumarizarea cu Ollama: {e}")
                
                self.history = [system_prompt] + self.history[-6:]
                logger.warning("Fallback aplicat: Am șters mesajele vechi în loc să le sumarizăm.")

    def clear_context(self):
        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.input_tokens = 0
        self.output_tokens = 0
        logger.info("Conversation context cleared.")

    # --- Persistence & Sessions Logic ---

    def export_to_json(self, filepath):
        import json
        data = {
            "messages": self.history,
            "input_tokens": getattr(self, 'input_tokens', 0),
            "output_tokens": getattr(self, 'output_tokens', 0)
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def import_from_json(self, filepath):
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.history = data.get("messages", [])
            self.input_tokens = data.get("input_tokens", 0)
            self.output_tokens = data.get("output_tokens", 0)
            return True
        except Exception as e:
            return False