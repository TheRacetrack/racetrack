# Description
This is typical "adder" model, that will send RecordKeeper PEM every time it 
is called.  This is just for example, it's not the best RK practice 
(PEMs should be sent only for relevant business events).

# Deploying
Run `racetrack deploy` in this directory.

# Calling a Job
The model sums up given numbers. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7000/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect:
# 42
```

# Health
The following request checks service's healthiness:
```bash
curl "http://localhost:7000/health" 
# Expect:
# {"service": "job", "status": "pass"}
```

# API docs
Check out root endpoint [http://localhost:7000/](http://localhost:7000/) with 
Swagger UI page containing interactive list of all endpoints.
