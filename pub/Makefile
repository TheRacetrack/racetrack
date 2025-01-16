.PHONY: run test send-payload-get send-payload-post

JOB ?= adder
ESC_TOKEN ?= 'token-unset'

run-auth:
	AUTH_REQUIRED=true AUTH_DEBUG=true LIFECYCLE_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2E3ZWNmODAtZDAxZS00ZjA5LWI4ZjQtMTZiNTMxYjhhOTNhIiwic3ViamVjdCI6InB1YiIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.Xyg1lwQG4oiA65y-KAkdmCFjnT7BZkfmm66DDGOVZu4 go run .

run:
	AUTH_REQUIRED=false AUTH_DEBUG=true LIFECYCLE_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2E3ZWNmODAtZDAxZS00ZjA5LWI4ZjQtMTZiNTMxYjhhOTNhIiwic3ViamVjdCI6InB1YiIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.Xyg1lwQG4oiA65y-KAkdmCFjnT7BZkfmm66DDGOVZu4 go run .

send-payload-get:
	curl -X GET --url http://127.0.0.1:7205/pub/job/$(JOB)/latest/

send-payload-get-auth:
	curl -X GET --url http://127.0.0.1:7205/pub/job/$(JOB)/latest/ -H "X-Racetrack-Esc-Auth: $(ESC_TOKEN)"

send-payload-post:
	curl -X POST --url http://127.0.0.1:7205/pub/job/$(JOB)/latest/api/v1/perform \
 	--header 'content-type: application/json' --data '{ "numbers": [40, 5] }'

send-payload-post-auth:
	curl -X POST --url http://127.0.0.1:7205/pub/job/$(JOB)/latest/api/v1/perform \
 	--header 'content-type: application/json' --data '{ "numbers": [40, 5] }' \
 	-H "X-Racetrack-Esc-Auth: $(ESC_TOKEN)"

 send-async-job-call:
	curl -X POST "http://127.0.0.1:7105/pub/async/new/job/adder/latest/api/v1/perform" \
		-H "Content-Type: application/json" \
		-H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
		-d '{"numbers": [40, 2]}'

test:
	go test -p 1 .

test-verbose:
	go test -p 1 -v .
