# Stress tests with Locust

## Testing production Racetrack

1. Copy `.env.template` to `.env`
1. Fillout missing values - `base_url`, `auth_token` to desired cluster
1. Deploy a Job
1. Create ESC, make adder allowed
1. Run `locust` (or `locust --tags perform` if you want to run single test case)
1. Open `http:0.0.0.0:8089`, set parameters, click `Start swarming`
1. Watch results

Alternatively, run locally:
```sh
ENV_FILE=.env locust --tags perform
```
