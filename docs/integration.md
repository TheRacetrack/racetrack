# Integration with Racetrack 

## Calling Jobs

Assuming you are ESC developer who wants to call certain Job:

1. Contact your Racetrack instance admin
2. Ask him to register your application as a consumer of Racetrack services, an ESC   
3. Receive the ESC auth, add in your call header:
   `'X-Racetrack-Esc-Auth': esc_auth` , ie.

```
racetrack_domain = 'https://...com"
pub_url = racetrack_domain + '/pub/job'
job_name = 'foobar'

r = requests.post(
      url=f'{pub_url}/{job_name}/{job_version}/api/v1/perform', 
      json={'numbers': [40, 2]}, 
      headers={'X-Racetrack-Esc-Auth': esc_auth}
      )
```

Note: if there are other proxies between you and RT, make sure to integrate with
them also, and check that they pass `X-Racetrack-Esc-Auth` header through.
