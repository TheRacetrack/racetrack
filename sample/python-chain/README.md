# Setup
1. Deploy "python-class" job (see [python-class](../python-class))
2. Deploy "python-chain" job by running `racetrack deploy` in this directory.
3. Create ESC and assign "python-chain" job to it in Racetrack admin panel: http://localhost:7103/lifecycle/admin
4. In Racetrack admin panel open "adder" job and add "python-chain" job to its "Allowed jobs".

# Calling a Job
This job calls another model suming up given numbers (good old "adder" model).
After getting partial result, it returns rounded integer.

The following request performs its functionality by calling it through PUB. Replace auth header with your ESC caller token.
```bash
curl -X POST "http://localhost:7105/pub/job/python-chain/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Esc-Auth: <insert your token here>" \
  -d '{"numbers": [40, 2.7]}'
# Expect:
# 43
```

# Health
The following request checks service's healthiness:
```bash
curl "http://localhost:7105/pub/job/python-chain/latest/health" 
# Expect:
# {"service": "job", "job_name": "python-chain", "status": "pass"}
```

# API docs
Check out root endpoint http://localhost:7005/pub/job/python-chain/latest/ with Swagger UI page containing interactive list of all endpoints.
