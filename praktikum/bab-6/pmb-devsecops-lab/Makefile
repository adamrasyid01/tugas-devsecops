.PHONY: setup validate build up down clean logs normal incident recover verify test evidence

setup:
	./scripts/setup.sh

validate:
	./scripts/validate.sh

build:
	docker compose build --pull

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

clean:
	docker compose down --volumes --remove-orphans

logs:
	docker compose logs --tail 100 --follow

normal:
	./scripts/demo-normal.sh

incident:
	./scripts/demo-incident.sh

recover:
	./scripts/set-incident.sh none

verify:
	./scripts/verify.sh

test:
	docker compose run --rm --no-deps registration-api python -m unittest discover -s tests -v

evidence:
	./scripts/collect-evidence.sh
