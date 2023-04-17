from fastapi import FastAPI

from dashboard.server.endpoint.account import setup_account_endpoints


def setup_api_endpoints(app: FastAPI):

    setup_account_endpoints(app)
