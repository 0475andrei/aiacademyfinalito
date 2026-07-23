import os
import platform
import threading
import time
from .tool import Tool

def perform_shutdown():
    # Wait for the user to read the message
    time.sleep(12) 
    
    system = platform.system().lower()
    if system == "windows":
        os.system("shutdown /s /t 1")
    elif system == "linux" or system == "darwin":
        os.system("sudo shutdown -h now")

def shutdown_callback():
    
    shutdown_thread = threading.Thread(target=perform_shutdown)
    shutdown_thread.start()
    
    # Return the message immediately to the chat interface
    return "gata, hai la bere!"

shutdown_tool = Tool(
    name="end_work_session",
    description="Use this when the user asks 'gata munca'. It shuts down the PC.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    callback=shutdown_callback
)