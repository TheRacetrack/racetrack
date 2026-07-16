# python-class4 — subtractfromlast

A sample Racetrack job that subtracts all elements from the last element.

For example, `[10, 3, 2]` returns `2 - 10 - 3 = -11`.

## Deploying

Run `racetrack deploy` in this directory.

## Calling a Job

```bash
curl -X POST "http://127.0.0.1:7105/pub/job/subtractfromlast/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"numbers": [10, 3, 2]}'
# Expect:
# -11.0
```

## Comparison

| Job | Sample input | Result | Logic |
|---|---|---|---|
| `python-class2/subtractor` | `[10, 3, 2]` | `5.0` | `first - rest` |
| `python-class21/subtractall` | `[10, 3, 2]` | `-15.0` | `0 - all` |
| `python-class4/subtractfromlast` | `[10, 3, 2]` | `-11.0` | `last - preceding` |

## API docs

Check out root endpoint [http://127.0.0.1:7105/pub/job/subtractfromlast/latest](http://127.0.0.1:7105/pub/job/subtractfromlast/latest)
with Swagger UI page containing interactive list of all endpoints.
