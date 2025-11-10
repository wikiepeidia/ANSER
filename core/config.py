# Core Configuration
class Config:
    SECRET_KEY = "fun-work-hub-secret-key-2025"
    DATABASE_PATH = "fun_work_hub.db"
    
    # UI Themes
    THEMES = {
        'auth': {
            'primary': '#00d4aa',
            'secondary': '#1a1a1a', 
            'background': '#0f0f0f',
            'surface': '#1a1a1a',
            'text': '#ffffff',
            'text_secondary': '#a0a0a0'
        },
        'workspace': {
            'primary': '#007acc',
            'secondary': '#252526',
            'background': '#1e1e1e',
            'sidebar': '#252526',
            'panel': '#2d2d30',
            'text': '#cccccc',
            'text_secondary': '#969696'
        }
    }
    
    # Workspace Types
    WORKSPACE_TYPES = [
        'personal',
        'team', 
        'scenarios',
        'projects'
    ]