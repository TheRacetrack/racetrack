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

# Calling auxiliary endpoints
The model has one auxiliary endpoint configured: `/explain`. 
It works similarly to `/perform` endpoint, but returns different result based on custom method implementation:
```bash
curl -X POST "http://localhost:7005/pub/job/python-auxiliary-endpoints/latest/api/v1/explain" \
  -H "Content-Type: application/json" \
  -d '{"x": 40, "y": 2}'
# Expect:
# {"x_importance": 0.9523809523809523, "y_importance": 0.047619047619047616}
```
