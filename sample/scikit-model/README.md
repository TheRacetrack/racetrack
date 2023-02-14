# Deploying
Run `racetrack deploy` in this directory.

# Calling a Job
The model uses linear regression to predict Y value for given data point.
X input data has 2 numerical features. Model accepts data point (composed of list of 2 floats) and returns list of predicted values for them. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7000/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"x_new": [0.5, 2]}'
# Expect:
# [201.96842858259438]
```

# Health
The following request checks service's healthiness:
```bash
curl "http://localhost:7000/health" 
# Expect:
# {"service": "job", "status": "pass"}
```

# API docs
Check out root endpoint [http://localhost:7000/](http://localhost:7000/) with Swagger UI page containing interactive list of all endpoints.
