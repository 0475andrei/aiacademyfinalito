import string
import secrets
from .tool import Tool


def password_analyzer_callback(password: str = "", generate_new: bool = False):
    """
    Checks password strength against corporate policies or generates a new one.
    """
    # 1. GENERATE A NEW PASSWORD
    if generate_new:
        alphabet = string.ascii_letters + string.digits + string.punctuation
        while True:
            # Generate a 16-character password
            pwd = ''.join(secrets.choice(alphabet) for i in range(16))
            # Ensure it meets all corporate requirements
            if (any(c.islower() for c in pwd)
                    and any(c.isupper() for c in pwd)
                    and any(c.isdigit() for c in pwd)
                    and any(c in string.punctuation for c in pwd)):
                return f"✅ Generated a highly secure password: {pwd}"

    # 2. CHECK AN EXISTING PASSWORD
    if not password:
        return "⚠️ Please provide a password to evaluate, or set 'generate_new' to True."

    missing_criteria = []
    
    
    if len(password) < 16:
        missing_criteria.append(f"Make it longer (currently {len(password)} chars, need at least 16)")
    
    if not any(c.islower() for c in password):
        missing_criteria.append("Add lowercase letters")
    
    if not any(c.isupper() for c in password):
        missing_criteria.append("Add uppercase letters")
    
    if not any(c.isdigit() for c in password):
        missing_criteria.append("Add at least one number")
    
    if not any(c in string.punctuation for c in password):
        missing_criteria.append("Add special characters (e.g., !@#$%^&*)")

    
    if not missing_criteria:
        return "✅ Password is very strong and meets all enterprise security criteria!"
    else:
        suggestions = "\n- ".join(missing_criteria)
        return f"❌ Password is weak. You need to improve the following:\n- {suggestions}"
    
    
    

password_tool = Tool(
    name="password_analyzer",
    description="Evaluates the strength of a user's password based on security policies, or generates a new strong, secure password.",
    parameters={
        "type": "object",
        "properties": {
            "password": {
                "type": "string",
                "description": "The password to evaluate. Leave empty if the user wants to generate a new one."
            },
            "generate_new": {
                "type": "boolean",
                "description": "Set to true if the user asks for a new password to be generated."
            }
        },
        "required": []
    },
    callback=password_analyzer_callback
)
