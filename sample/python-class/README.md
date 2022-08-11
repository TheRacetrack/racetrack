# Deploying
Run `racetrack deploy` in this directory.

# Calling a Fatman
The model sums up given numbers. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7105/pub/fatman/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0._XIg7ainazrLnU6-4pJ1BW63vPpgtX41O2RhxshW-E0" \
  -d '{"numbers": [40, 2]}'
# Expect:
# 42
```

# API docs
Check out root endpoint [http://localhost:7105/pub/fatman/adder/latest](http://localhost:7105/pub/fatman/adder/latest)
with Swagger UI page containing interactive list of all endpoints.
