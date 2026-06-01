from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from pathlib import Path
from .routes import router
from .service import WebService

def create_app(store, repo_root, provider_registry, **kwargs):
    app = FastAPI(title="OpenClaw Workspace")
    
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))
    app.state.service = WebService(store, repo_root)
    
    # Inject context variables as needed by templates
    # This is a simplified version of the original context logic
    
    app.include_router(router)
    return app
