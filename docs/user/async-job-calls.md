# Asynchronous calls to jobs

Classic calls to the jobs are made synchronously.
While it's fine for short requests, it's not suitable for the very long requests,
which may end with the timeout errors, imposed by the proxy in-between.

Synchronous calls are still recommended for short requests (up to 30 seconds),
especially for serving static resources or webview pages. 
For long requests, it might be better to use the asynchronous approach described below.

## Asynchronous call to a job

Racetrack exposes special endpoints for making asynchronous calls to the jobs.

Instead of waiting for a long request to complete,
a client can initiate a new task and immediately receive a task ID.
The client then makes another request, this time to a different endpoint, to check the status of the task using the given ID. 
The task is processed in the background by Racetrack, utilizing the same classic synchronous call to a job under the hood.
This means no modifications are needed on the job's end.

This is an opt-in feature for clients, classic synchronous calls are still be available.

The main idea is to split a long request into 2 parts:

1. **Start a new task** - a user makes one request to start a task and get the immediate response with the ID of the task. The task is then scheduled and processed by a job.
2. **Check on the result** - a user checks in a loop if a requested task is already done. If so, he gets a response.

The latter endpoint uses the HTTP Long Polling technique,
which makes client to wait until task is completed or timeout is reached.
Client gets notified as soon as the task is completed, without the need to poll the server periodically.
If a timeout occurs or the connection is lost for any reason,
the client can simply resend the request without any loss,
as the final result can still be retrieved using the task's ID.

Using long polling instead of the periodic polling (eg. every 5 seconds) reduces the number of requests and the load on the server.
Plus, client gets a real-time response, as soon as the task is completed.

## API reference
Pub component (Racetrack's gateway) will expose 2 new endpoints for making the asynchronous calls to the jobs
(beside the classic synchronous endpoint):

### 1. Starting async task
This endpoint starts a new task for calling a job,
and responds with a JSON containing the unique ID of the task.

#### Request
`POST` `/pub/async/new/job/{job_name}/{job_version}/{job_path}`

Path parameters:
- `job_name` (**string**) - the name of the job, eg. `adder`
- `job_version` (**string**) - the version of the job, eg. `1.0.0` or `latest`
- `job_path` (**string**) - the path to the job, eg. `api/v1/perform`

Body (**application/json**):
- input parameters to the job (the same as for the classic synchronous call)

#### Response
- `201 Created` - if task has been created successfully. Response is the JSON payload with the following fields:
    - `task_id` (**string**) - a unique UUID identifier of the task
- `500 Internal Server Error` -
  the task has failed. Details of an error will be included in the HTTP body.
- `503 Service Unavailable` -
  Racetrack is currently in maintenance mode. Try again later.

#### Request / Response Sample
```sh
curl --request POST \
  --url http://127.0.0.1:7005/pub/async/new/job/adder/1.0.0/api/v1/perform \
  --header 'Content-Type: application/json' \
  --header 'X-Racetrack-Auth: eyJhbGciOiJIUz' \
  --data '{ "numbers": [40, 2] }'
```
```
HTTP/1.1 201 Created
Content-Type: application/json

{
    "task_id": "16b472ec-77c7-464a-932c-1cb2efc3e728"
}
```

### 2. Polling for the result
This endpoint checks the status of the task and responds with a JSON containing the result of the task.

#### Request
`GET` `/pub/async/task/{task_id}/poll`

Path parameters:
- `task_id` (**string**) - the unique UUID identifier of the task, received from the previous endpoint

#### Response

- `200 OK` -
  the task has completed successfully, the response payload contains the result of the job call
  in the JSON format (in the same format returned by the classic synchronous call)
  with the original HTTP status code and the headers.
- `202 Accepted`, `408 Request Timeout` or `504 Gateway Timeout` -
  the task is still in progress, the client should repeat the request
- `404 Not Found` -
  This error indicates that the task ID provided is invalid or the task is not found.
- `500 Internal Server Error` -
  the task has failed.
  Details of an error will be included in the HTTP body in the JSON format with the following fields:
    - `error` (**string**) - description of the error cause
- `503 Service Unavailable` -
  Racetrack is currently in maintenance mode. Try again later.

#### Request / Response Sample
```sh
curl --request GET \
  --url http://127.0.0.1:7005/pub/async/task/16b472ec-77c7-464a-932c-1cb2efc3e728/poll \
  --header 'X-Racetrack-Auth: eyJhbGciOiJIUz'
```
```
HTTP/1.1 200 OK
Content-Type: application/json

42
```

### 3. Checking status of the task
This is an optional endpoint for checking the current status of the task.
This endpoint should return immediately, without waiting for the task to complete.

#### Request
`GET` `/pub/async/task/{task_id}/status`

Path parameters:
- `task_id` (**string**) - the unique UUID identifier of the task

#### Response
- `200 OK` - if task exists. Response is the JSON payload with the following fields:
    - `task_id` (**string**) - a unique UUID identifier of the task
    - `status` (**string**) - current status of a task. Can be one of the following:
        - `ongoing` - the task is still in progress
        - `completed` - the task has successfully completed and it's ready to retrieve the result
        - `failed` - the task has failed. Error details can be checked at the polling endpoint.
- `404 Not Found` -
  This indicates that the task ID provided is invalid or the task is not found.

#### Request / Response Sample
```sh
curl --request GET \
  --url http://127.0.0.1:7005/pub/async/task/16b472ec-77c7-464a-932c-1cb2efc3e728/status \
  --header 'X-Racetrack-Auth: eyJhbGciOiJIUz'
```
```
HTTP/1.1 200 OK
Content-Type: application/json

{
    "task_id": "16b472ec-77c7-464a-932c-1cb2efc3e728",
    "status": "ongoing"
}
```

## Sample client implementation in Python
```sh
pip install httpx
```
```python
import httpx

pub_url = 'http://127.0.0.1:7005'
job_name = 'windows12'
job_version = 'latest'
job_path = 'api/v1/perform'
payload = {"mode": "timeout", "t": 121}
auth_token = 'eyJhbGciOiJ...'

# 1. Start async task
response = httpx.post(f'{pub_url}/pub/async/new/job/{job_name}/{job_version}/{job_path}', headers={
    'X-Racetrack-Auth': auth_token,
}, json=payload)
task_id: str = response.json()['task_id']

# 2. Wait for the result
while True:
    print('Are we there yet?...')
    try:
        response = httpx.get(f'{pub_url}/pub/async/task/{task_id}/poll', timeout=httpx.Timeout(5, read=60))
    except httpx.ReadTimeout as e:
        print('Read timeout')
        continue
    if response.status_code == 200:  
        break
    elif response.status_code in {202, 408, 504}:
        print(f'Response {response.status_code} {response.reason_phrase}')
        continue
    else:
        raise RuntimeError(f'Response error: {response}')

result = response.json()
```

## Details
- To provide the result of the task to the client,
  Racetrack has to keep the result in memory for a certain period of time.
- Additionaly, it will store the records of the ongoing tasks in the database,
  to continue working on them after a server restart (e.g. due to the upgrade).
- The result are removed from the memory (and the database) right after the client retrieves the result.
  So that **it can't be retrieved again**.
  To accommodate any potential timeouts during the retrieval process,
  we allow a grace period of 10 seconds post-retrieval before the result is eventually removed.
- The task's result will be removed from the memory (and the database) after a certain period of time,
  even if the client didn't retrieve it. This timeout is set to **120 minutes**.
- Racetrack doesn't keep the ongoing tasks that stuck forever on the job's end.
  There is a hard timeout for the task, set to **120 minutes**.
- If the Racetrack servers are restarted (for instance, during an upgrade),
  the ongoing tasks will be resumed.
- Multiple replicas of the Pub component (Racetrack's gateway)
  communicate with each other to share the tasks and the results, so the result can be retrieved from any of them.
- The timeout for long polling is configured to **30 seconds**.
  This implies that the server will terminate the polling endpoint after 30 seconds of no activity.
  Consequently, the client will renew the request every 30 seconds in a loop, until the task is completed.
- If a connection to a job is lost (eg. due to Out of Memory kill),
  the task will be retried automatically until reaching the maximum number of attempts (set to **2** by default).
