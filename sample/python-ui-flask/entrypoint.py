from typing import List

from flask import render_template, Flask, request, jsonify


class JobEntrypoint:
    def perform(self, numbers: List[float]) -> float:
        """Return sum of given numbers"""
        return sum(numbers)

    def webview_app(self, base_url: str):
        """
        Create WSGI app serving custom UI pages
        :param base_url Base URL prefix where WSGI app is deployed.
        """
        app = Flask(__name__, template_folder='templates')

        @app.errorhandler(404)
        def page_not_found(e):
            return f'requested path was not found: {request.path}', 404

        @app.route(base_url + '/')
        def index():
            return render_template('index.html', base_url=base_url)

        @app.route(base_url + '/postme', methods=['POST'])
        def postme():
            return jsonify({"hello": request.json})

        @app.route(base_url + '/describe', methods=['GET', 'POST'])
        def describe():
            return jsonify({
                "request.method": request.method,
                "request.path": request.path,
                "request.full_path": request.full_path,
                "request.headers": {h: request.headers.get(h) for h in request.headers.keys()},
                "request.data": request.data.decode(),
                "request.remote_addr": request.remote_addr,
                "request.host": request.host,
            })

        return app.wsgi_app
