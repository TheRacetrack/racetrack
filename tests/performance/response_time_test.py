import os
import statistics
import time

import httpx
from dotenv import load_dotenv


load_dotenv()

url = os.environ['url']
auth_token = os.environ.get('auth_token', '')
payload = os.environ.get('payload')
attempts = int(os.environ.get('attempts', 100))
auth_header = os.environ.get('auth_header', 'X-Racetrack-Auth')

headers = {
    'User-Agent': 'curl/7.81.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    auth_header: auth_token,
}

reuse_connection = True

print(f'Testing URL {url}')

durations = []
client = httpx.Client()
try:
    for i in range(attempts):

        if reuse_connection:
            response = client.post(url, timeout=30, headers=headers, content=payload)

        else:
            response = httpx.post(url, timeout=30, headers=headers, content=payload)

        duration = response.elapsed.total_seconds()

        time.sleep(1)
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
