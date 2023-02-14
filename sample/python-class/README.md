# Deploying
Run `racetrack deploy` in this directory.

# Calling a Job
The model sums up given numbers. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7105/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"numbers": [40, 2]}'
# Expect:
# 42
```

# API docs
Check out root endpoint [http://localhost:7105/pub/job/adder/latest](http://localhost:7105/pub/job/adder/latest)
with Swagger UI page containing interactive list of all endpoints.
