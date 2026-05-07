from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def setup_web_views(app: FastAPI):

    @app.get("/", tags=['ui'])
    def _ui_root_view():
        return RedirectResponse('/dashboard/ui/')

    @app.get("/ui", tags=['ui'])
    def _ui_home_view():
        return FileResponse('static/index.html')

    @app.get("/ui/", tags=['ui'])
    def _ui_home_slash_view():
        return FileResponse('static/index.html')

    if Path('static/assets').is_dir():
        app.mount("/ui/assets", StaticFiles(directory="static/assets/"), name="static_front")
    else:
        logger.warning('No static/assets directory found')

    @app.get("/ui/{subpath:path}", tags=['ui'])
    def _ui_home_any_view(subpath: str):
        return FileResponse('static/index.html')
