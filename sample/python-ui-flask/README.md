# Deploying
Run `racetrack deploy` in this directory.

# Calling a Job
This job sums up given numbers. 

The following request performs its functionality by calling it through PUB:
```bash
curl -X POST "http://localhost:7005/pub/job/python-ui-flask/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect:
# 42
```

# Health
The following request checks service's healthiness:
```bash
curl "http://localhost:7005/pub/job/python-ui-flask/latest/health" 
# Expect:
# {"service": "job", "status": "pass"}
```

# API docs
Every endpoint is served with PUB prefix path: `/pub/job/python-ui-flask/latest`.
Check out root endpoint http://localhost:7005/pub/job/python-ui-flask/latest/ with Swagger UI page containing interactive list of all endpoints.

# Webview UI
The job exposes custom UI pages available through PUB at:
http://localhost:7005/pub/job/python-ui-flask/latest/api/v1/webview

It also exposes a sample POST endpoint for some internal webview communication:
```bash
curl -X POST "http://localhost:7005/pub/job/python-ui-flask/latest/api/v1/webview/postme" \
  -H "Content-Type: application/json" \
  -d '"World"'
# Expect:
# {"hello": "World"}
```
