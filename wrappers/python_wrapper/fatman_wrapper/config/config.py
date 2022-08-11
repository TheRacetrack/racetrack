from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.forbid):
    """Configuration for Fatman Wrapper embedding model in a server"""

    # Log level: debug, info, warn, error
    log_level: str = 'debug'

    # API endpoints
    http_addr: str = '0.0.0.0'
    http_port: int = 7000
