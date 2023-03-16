import os
import statistics
import sys
import time

import httpx
from dotenv import load_dotenv


load_dotenv(sys.argv[1])

url = os.environ['url']
attempts = int(os.environ.get('attempts', 100))
payload = os.environ.get('payload')
auth_header = os.environ.get('auth_header', 'X-Racetrack-Auth')
auth_token = os.environ.get('auth_token', '')
reuse_connection: bool = os.environ.get('reuse_connection', 'true').lower() in {'true', '1'}

print(f'Testing URL {url}')
print(f'attempts: {attempts}, reuse_connection (connection pool): {reuse_connection}, payload: {payload}')

durations = []
headers = {
    'User-Agent': 'curl/7.81.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    auth_header: auth_token,
}
client = httpx.Client()
try:
    for i in range(attempts):

        if reuse_connection:
            response = client.post(url, timeout=30, headers=headers, content=payload)

        else:
            response = httpx.post(url, timeout=30, headers=headers, content=payload)

        duration = response.elapsed.total_seconds()

        response.raise_for_status()
        durations.append(duration)
        print(f'Attempt #{i+1} - request duration: {duration*1000:.2f} ms')
except KeyboardInterrupt:
    pass
finally:
    client.close()

average = sum(durations) / len(durations)
min_duration = min(durations)
max_duration = max(durations)
median = statistics.median(durations)
print(f'----------')
print(f'Requests: {len(durations)}')
print(f'Median: {median*1000:.2f} ms')
print(f'Average: {average*1000:.2f} ms')
print(f'Min: {min_duration*1000:.2f} ms')
print(f'Max: {max_duration*1000:.2f} ms')
