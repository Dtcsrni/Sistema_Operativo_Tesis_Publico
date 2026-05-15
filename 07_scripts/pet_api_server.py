#!/usr/bin/env python3
"""Servidor FastAPI para Web API de OpenClaw PET bundles."""

import sys
from pathlib import Path

try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    print("Error: Se requieren fastapi y uvicorn")
    print("Instala con: pip install fastapi uvicorn")
    sys.exit(1)

# Agregar runtime/openclaw al path para resolver el paquete openclaw_local
root = Path(__file__).resolve().parent.parent
runtime_openclaw = root / "runtime" / "openclaw"
sys.path.insert(0, str(runtime_openclaw))

from openclaw_local.storage import OpenClawStore
from openclaw_local.web_pet import register_pet_routes


def create_pet_api_app(store_path: str = "runtime/openclaw/openclaw_store.db", store = None) -> FastAPI:
    """Crea la aplicación FastAPI con rutas de PET.

    Args:
        store_path: Ruta a la base de datos SQLite (ignorada si store no es None)
        store: Instancia de OpenClawStore (si se pasa, se usa en lugar de crear una nueva)

    Returns:
        Instancia configurada de FastAPI
    """
    app = FastAPI(
        title="OpenClaw PET API",
        description="Web API para ingesta y consulta de PET bundles académicos",
        version="1.0.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Storage
    if store is None:
        store = OpenClawStore(store_path)

    # Rutas PET
    register_pet_routes(app, store)

    # Health check
    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    # Raíz
    @app.get("/")
    async def root() -> dict:
        return {
            "name": "OpenClaw PET API",
            "version": "1.0.0",
            "endpoints": {
                "POST": "/api/v1/pet/ingest",
                "GET": "/api/v1/pet/<bundle_id>",
                "GET": "/api/v1/pet/list",
                "GET": "/api/v1/pet/<bundle_id>/claims",
                "GET": "/api/v1/pet/<bundle_id>/fragments",
            },
        }

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Servidor FastAPI para OpenClaw PET API")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Puerto (default 8001)")
    parser.add_argument("--db", default="runtime/openclaw/openclaw_store.db", help="Ruta DB")
    parser.add_argument("--reload", action="store_true", help="Auto-reload en cambios")

    args = parser.parse_args()

    app = create_pet_api_app(store_path=args.db)

    print(f"🚀 Iniciando OpenClaw PET API en {args.host}:{args.port}")
    print(f"📖 Docs: http://{args.host}:{args.port}/docs")

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
