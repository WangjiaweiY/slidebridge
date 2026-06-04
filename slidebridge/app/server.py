from __future__ import annotations

import json
import secrets
from pathlib import Path
from string import Template
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from slidebridge import __version__
from slidebridge.app.remote import RemoteConnection, list_remote_directory, test_remote_connection, test_ssh_connection
from slidebridge.app.sessions import ViewerSessionManager
from slidebridge.remote.profiles import load_profiles


NO_STORE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Expires": "0",
}


def create_launcher_app(session_manager: ViewerSessionManager | None = None) -> FastAPI:
    manager = session_manager or ViewerSessionManager()
    root = Path(__file__).parent
    static_root = root / "static"
    template_path = root / "templates" / "app.html"
    static_cache_key = secrets.token_hex(8)
    app = FastAPI(title="SlideBridge App", version=__version__)
    app.mount("/static", StaticFiles(directory=static_root), name="slidebridge-app-static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        config = {
            "version": __version__,
            "profiles": [profile.to_dict() for profile in sorted(load_profiles().values(), key=lambda item: item.name)],
        }
        template = Template(template_path.read_text(encoding="utf-8"))
        return HTMLResponse(
            template.substitute(
                app_config_json=json.dumps(config, ensure_ascii=False).replace("</", "<\\/"),
                static_cache_key=static_cache_key,
            ),
            headers=NO_STORE_HEADERS,
        )

    @app.get("/api/profiles")
    def api_profiles() -> JSONResponse:
        return _json_response({
            "profiles": [profile.to_dict() for profile in sorted(load_profiles().values(), key=lambda item: item.name)]
        })

    @app.post("/api/remote/test")
    def api_remote_test(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = test_ssh_connection(RemoteConnection.from_payload(payload), timeout=float(payload.get("timeout") or 20.0))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response({
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })

    @app.post("/api/remote/runtime-test")
    def api_remote_runtime_test(payload: dict[str, Any]) -> JSONResponse:
        try:
            result = test_remote_connection(RemoteConnection.from_payload(payload), timeout=float(payload.get("timeout") or 20.0))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response({
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })

    @app.post("/api/remote/list")
    def api_remote_list(payload: dict[str, Any]) -> JSONResponse:
        try:
            connection = RemoteConnection.from_payload(payload)
            entries, result = list_remote_directory(
                connection,
                str(payload.get("remote_dir") or payload.get("remote_path") or ""),
                limit=int(payload.get("limit") or 500),
                timeout=float(payload.get("timeout") or 30.0),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response({
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "entries": entries,
        })

    @app.post("/api/session/command")
    def api_session_command(payload: dict[str, Any]) -> JSONResponse:
        try:
            session = manager.prepare_remote(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response(session.to_dict())

    @app.post("/api/session/launch")
    def api_session_launch(payload: dict[str, Any]) -> JSONResponse:
        try:
            session = manager.launch_remote(payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response(session.to_dict())

    @app.get("/api/session/list")
    def api_session_list() -> JSONResponse:
        return _json_response({"sessions": manager.list_sessions()})

    @app.post("/api/session/{session_id}/stop")
    def api_session_stop(session_id: str) -> JSONResponse:
        try:
            session = manager.stop(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _json_response(session.to_dict())

    return app


def _json_response(payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(payload, headers=NO_STORE_HEADERS)
