import re
from models import Language

# Python-specific patterns that don't exist in JavaScript
PYTHON_SIGNALS = [
    r'\bdef\s+\w+\s*\(',       
    r'\bimport\s+\w+',          
    r'\bfrom\s+\w+\s+import\b', 
    r'\bprint\s*\(',            
    r':\s*$',                  
    r'\bself\b',                
    r'\belif\b',                
]

# JavaScript-specific patterns that don't exist in Python
JS_SIGNALS = [
    r'\bconst\s+\w+',           
    r'\blet\s+\w+',             
    r'\bvar\s+\w+',           
    r'\bfunction\s+\w+\s*\(',  
    r'=>',                       
    r'\bconsole\.log\s*\(',     
    r'\bdocument\.',           
    r'===|!==',                 
]

def detect_language(code: str, filename: str | None = None) -> Language:
    if filename:
        if filename.endswith((".py",)):
            return "python"
        if filename.endswith((".js", ".ts", ".jsx", ".tsx")):
            return "javascript"

    
    python_score = sum(
        1 for pattern in PYTHON_SIGNALS
        if re.search(pattern, code, re.MULTILINE)
    )
    js_score = sum(
        1 for pattern in JS_SIGNALS
        if re.search(pattern, code, re.MULTILINE)
    )

    if python_score == 0 and js_score == 0:
        return "python"

    return "python" if python_score >= js_score else "javascript"