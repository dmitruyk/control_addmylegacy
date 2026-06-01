.DEFAULT_GOAL := test

port ?= 8000
service_name ?= control-addmylegacy-backend
version ?= 0.0.1
image_tag ?= $(service_name):$(version)
registry ?= 192.168.0.230:5005
registry_image ?= $(registry)/$(service_name):latest
docker_context ?= .
dockerfile ?= Dockerfile
env_file ?= .env

.PHONY: test
test:
	python manage.py test

.PHONY: migrate
migrate:
	python manage.py migrate --noinput

.PHONY: build-css
build-css:
	npm ci
	npm run build:css

.PHONY: collectstatic
collectstatic:
	DJANGO_SETTINGS_MODULE=config.settings python manage.py collectstatic --noinput

.PHONY: env-file
env-file:
	@test -f $(env_file) || (cp .env.example $(env_file) && echo "Created $(env_file) from .env.example")

.PHONY: build-docker
build-docker: env-file
	docker build --file $(dockerfile) --tag $(image_tag) $(docker_context)

.PHONY: tag-docker
tag-docker:
	docker tag $(image_tag) $(registry_image)

.PHONY: push-docker
push-docker: tag-docker
	docker push $(registry_image)

.PHONY: build-push-docker
build-push-docker:
	$(MAKE) build-docker
	$(MAKE) push-docker

.PHONY: run-docker
run-docker:
	docker run --rm -p $(port):8000 --env-file $(env_file) $(image_tag)

.PHONY: login-registry
login-registry:
	docker login $(registry)

.PHONY: build-missing-static
build-missing-static:
	python3 deploy/build_missing_static.py

.PHONY: deploy-placeholder
deploy-placeholder: build-missing-static
	@echo "Install static /missing on NAS (required when Docker is stopped):"
	@echo "  make install-nginx-placeholder NGINX_ROOT=/volume1/web/control-addmylegacy"
	@echo "Normal deploy: bump STATIC_BUILD_ID and make build-push-docker"

.PHONY: install-nginx-placeholder
install-nginx-placeholder: build-missing-static
	./deploy/install-updating-placeholder.sh $(NGINX_ROOT)

.PHONY: clean-docker
clean-docker:
	-docker rmi $(image_tag)
	-docker rmi $(registry_image)
