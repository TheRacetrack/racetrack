# Stress tests with Locust

## Testing production Racetrack

1. Copy `.env.template` to `.env`
1. Fillout missing values - test_env=kubernetes to desired cluster
1. Deploy Job adder
1. Create ESC, make adder allowed, and put its auth to esc_auth
1. Run `locust` (or `locust --tags perform` if you want to run single test case)
1. Open `http:0.0.0.0:8089`, set parameters, click `Start swarming`
1. Watch results

## Testing localhost on docker compose

1. Run `make compose-run-stress`
1. Deploy Job adder
1. Open `http:0.0.0.0:8089`, set parameters, click `Start swarming`
1. Watch results

Alternatively, run locally:
```sh
ENV_FILE=.env locust --tags perform
```

## Testing localhost on kind

1. Run `make kind-up`
2. Deploy Job adder
3. Copy .env.dist to .env
4. Fillout missing values - test_env=kind
5. Run `export LIFECYCLE_URL=http://127.0.0.1:7002 locust`
6. Open `http:0.0.0.0:8089`, set parameters, click `Start swarming`
7. Watch results
