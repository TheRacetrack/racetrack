# Calling a Job
The model sums up given numbers. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7005/pub/job/python-auxiliary-endpoints/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"x": 40, "y": 2}'
# Expect:
# 42
```

# Calling static endpoints
The model has a few static endpoints configured.
GET request simply retrieves the file:
```bash
curl "http://localhost:7005/pub/job/python-static-endpoints/latest/api/v1/xrai"
# Expect xrai.yaml content

curl "http://localhost:7005/pub/job/python-static-endpoints/latest/api/v1/manifest" -v
# Expect job.yaml content with Content-Type "application/x-yaml"

curl "http://localhost:7005/pub/job/python-static-endpoints/latest/api/v1/docs/readme" -v
# Expect README.md content with Content-Type "text/plain"
```
