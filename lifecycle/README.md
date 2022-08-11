# LC API Server
LC server is an API Server for managing deployed Fatman workloads. 
In particular, it's the entypoint for a Developer when deploying a new Fatman Workload.

# Testing
Run the following command to perform unit tests:
```bash
make test
```

# Run
Run local LC-API server:
```bash
make run
```

By default localhost LC-API will use sqlite db. In docker-compose and kind setups
it will use Postgres.

