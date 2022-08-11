DOCKER_DAEMON_HOST_IP ?= 127.0.0.1

start-docker-daemon:
	docker run -it --rm \
		--name dind \
		-p 2376:2376 -p 7000:7000 -p 7010:7010 \
		--privileged \
		-v ./certs:/certs \
		--add-host=host.docker.internal:host-gateway \
		docker:dind \
		--tlsverify --tlscacert=/certs/ca.pem --tlscert=/certs/server-cert.pem --tlskey=/certs/server-key.pem \
		-H=0.0.0.0:2376 \
		--insecure-registry=host.docker.internal:5000

test-client:
	DOCKER_HOST=tcp://$(DOCKER_DAEMON_HOST_IP):2376 DOCKER_TLS_VERIFY=1 DOCKER_CERT_PATH=./certs docker ps
