# Start / upgrade Racetrack
up:
	DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false docker compose up -d --no-build --pull=always

status:
	docker compose ps

logs:
	docker compose logs

# Stop the instance
down:
	DOCKER_BUILDKIT=1 docker compose down

clean: down
	rm -rf .plugins
