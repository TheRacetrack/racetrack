from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse


def setup_web_views(app: FastAPI):

    @app.get("/", tags=['ui'])
    async def _ui_root_view():
        return RedirectResponse('/dashboard/ui/')
    
    @app.get("/ui", tags=['ui'])
    async def _ui_home_view():
        return FileResponse('static/index.html')
    
    @app.get("/ui/", tags=['ui'])
    async def _ui_home_slash_view():
        return FileResponse('static/index.html')

    app.mount("/ui/assets", StaticFiles(directory="static/assets/"), name="static_front")
    
    @app.get("/ui/{subpath:path}", tags=['ui'])
    async def _ui_home_any_view(subpath: str):
        return FileResponse('static/index.html')
