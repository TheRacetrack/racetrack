.PHONY: run test send-payload-get send-payload-post

FATMAN ?= adder
ESC_TOKEN ?= 'token-unset'

run-auth:
	AUTH_REQUIRED=true AUTH_DEBUG=true LIFECYCLE_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2E3ZWNmODAtZDAxZS00ZjA5LWI4ZjQtMTZiNTMxYjhhOTNhIiwic3ViamVjdCI6InB1YiIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.Xyg1lwQG4oiA65y-KAkdmCFjnT7BZkfmm66DDGOVZu4 go run .

run:
	AUTH_REQUIRED=false AUTH_DEBUG=true LIFECYCLE_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2E3ZWNmODAtZDAxZS00ZjA5LWI4ZjQtMTZiNTMxYjhhOTNhIiwic3ViamVjdCI6InB1YiIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.Xyg1lwQG4oiA65y-KAkdmCFjnT7BZkfmm66DDGOVZu4 go run .

send-payload-get:
	curl -X GET --url http://localhost:7205/pub/fatman/$(FATMAN)/latest/

send-payload-get-auth:
	curl -X GET --url http://localhost:7205/pub/fatman/$(FATMAN)/latest/ -H "X-Racetrack-Esc-Auth: $(ESC_TOKEN)"

send-payload-post:
	curl -X POST --url http://localhost:7205/pub/fatman/$(FATMAN)/latest/api/v1/perform \
 	--header 'content-type: application/json' --data '{ "numbers": [40, 5] }'

send-payload-post-auth:
	curl -X POST --url http://localhost:7205/pub/fatman/$(FATMAN)/latest/api/v1/perform \
 	--header 'content-type: application/json' --data '{ "numbers": [40, 5] }' \
 	-H "X-Racetrack-Esc-Auth: $(ESC_TOKEN)"

test:
	go test .
