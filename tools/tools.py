from .lucky_number_tool import lucky_number_tool
from .search_tool import search_tool
from .phishing_tool import PhishingAnalysisTool
from .guide_tool import CybersecGuideTool
from .password_tool import password_tool
from .shutdown_tool import shutdown_tool

tools = [
    lucky_number_tool, 
    search_tool,
    PhishingAnalysisTool(), 
    CybersecGuideTool(),
    password_tool,
    shutdown_tool
]