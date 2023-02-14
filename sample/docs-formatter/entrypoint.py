import base64
import zlib

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND
import markdown


class JobEntrypoint:

    def webview_app(self, base_url: str):
        """
        Create ASGI app serving custom UI pages
        :param base_url Base URL prefix where WSGI app is deployed.
        """
        app = FastAPI()
        templates = Jinja2Templates(directory="templates")

        @app.get('/')
        async def _index(request: Request):
            return RedirectResponse(f"{base_url}/view")

        @app.get('/view')
        async def _view(request: Request, data: str = ''):
            if data:
                raw_docs = decode_docs(data)
            else:
                raw_docs = ''
            html_docs = generate_html_docs(raw_docs)

            return templates.TemplateResponse("view.html", {
                'request': request,
                'base_url': base_url,
                'raw_docs': raw_docs,
                'html_docs': html_docs,
            })

        @app.post('/preview')
        async def _render(request: Request, raw_docs: str = Form('')):
            encoded_docs = encode_docs(raw_docs.replace('\r\n', '\n'))
            return RedirectResponse(f"{base_url}/view?data={encoded_docs}", status_code=HTTP_302_FOUND)

        return app


def encode_docs(raw_docs: str) -> str:
    compressed = zlib.compress(raw_docs.encode())
    b64: bytes = base64.b64encode(compressed)
    # encode URL-forbidden characters
    return b64.decode().replace("+", ".").replace("/", "_").replace("=", "-")


def decode_docs(url_data: str) -> str:
    # decode URL-forbidden characters
    b64 = url_data.replace(".", "+").replace("_", "/").replace("-", "=").encode()
    compressed = base64.b64decode(b64)
    decompressed: bytes = zlib.decompress(compressed)
    return decompressed.decode()


def generate_html_docs(markdown_content: str) -> str:
    # add missing blank lines before enumeration
    markdown_content = markdown_content.replace(':\n- ', ':\n\n- ')
    return markdown.markdown(markdown_content, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.sane_lists',
    ])
