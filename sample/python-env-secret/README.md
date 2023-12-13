# Deploying a Job
This Job makes use of secret vars, it should be filled out before attempting to deploy.
1. Make secret files from the templates:
    ```
    cp build.env.template build.env
    cp runtime.env.template runtime.env
    ```
2. Edit `build.env` and `runtime.env` files and fill out your secrets.
3. Ensure the secret files are ignored by git.
4. Deploy the sample.

# Calling a Job
The Job generates random number and prints env vars configured in job.yaml and loaded from secret files. 
The following request performs its functionality:
```bash
curl -X POST "http://127.0.0.1:7005/pub/job/python-env-secret/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expect:
# {
#  "model": "zoo",
#  "result": 0.844725159639815,
#  "passwd": "itworks!"
# }
```
