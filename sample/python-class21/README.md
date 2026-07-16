# python-class21 — subtractall

A sample Racetrack job that subtracts all numbers from zero (i.e. returns the negated sum).

## Deploying

Run `racetrack deploy` in this directory.

## Calling a Job

The model subtracts all numbers from zero: `0 - a - b - c - ...`

```bash
curl -X POST "http://127.0.0.1:7105/pub/job/subtractall/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"numbers": [10, 3]}'
# Expect:
# -13.0
```

Compare with `python-class2/subtractor` which returns `first - rest` (e.g. `10 - 3 = 7`).

## API docs

Check out root endpoint [http://127.0.0.1:7105/pub/job/subtractall/latest](http://127.0.0.1:7105/pub/job/subtractall/latest)
with Swagger UI page containing interactive list of all endpoints.
