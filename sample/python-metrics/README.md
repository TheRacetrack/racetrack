# Calling a Job
The model generates random number. 
The following request performs its functionality:
```bash
curl -X POST "http://localhost:7005/pub/job/python-metrics/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expect:
# 0.5
```

# Metrics
Fetch `/metrics` endpoint to see Prometheus metrics values (generic metrics as well as the custom ones).
```bash
curl "http://localhost:7005/pub/job/python-metrics/latest/metrics"
# Expect:
# perform_requests_total 17.0
# ...
# # HELP job_wasted_seconds Seconds you have wasted here
# job_wasted_seconds 1.2
# # HELP job_positives Number of positive results
# job_positives{color="blue"} 5.0
```
