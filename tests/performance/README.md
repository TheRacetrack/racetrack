# Test response times of Racetrack's jobs

1. Install
```sh
pip install -r requirements.txt
```

2. Copy `.env.template` to `*.env` and fillout missing values:
```sh
cp .env.template test.env
```

3. Run performance test:
```sh
python response_time_test.py test.env
```
