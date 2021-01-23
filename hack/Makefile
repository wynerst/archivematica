.DEFAULT_GOAL := help

# Ensure that Composes uses BuildKit.
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Paths for Docker named volumes
AM_PIPELINE_DATA ?= $(HOME)/.am/am-pipeline-data
SS_LOCATION_DATA ?= $(HOME)/.am/ss-location-data

CALLER_UID=$(shell id -u)
CALLER_GID=$(shell id -g)

SRCDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../src)
AMDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)

TOXARGS ?=

define compose_amauat
	docker-compose -f docker-compose.yml -f docker-compose.acceptance-tests.yml $(1)
endef

define compose_tests
	docker-compose -f docker-compose.yml -f docker-compose.tests.yml $(1)
endef

empty :=
space := $(empty) $(empty)
define toxenvs
	$(call compose_tests, \
		run \
			--user $(CALLER_UID):$(CALLER_GID) \
			--workdir /src \
			--rm \
			--no-deps \
			--entrypoint tox \
				archivematica-tests \
					$(subst $(space), -e ,$(space)$(1)) \
					$(TOXARGS))
endef
define toxenvs_integration
	$(call compose_tests, \
		run \
			-e PRE_COMMAND="{toxinidir}/hack/wait-for-it.sh mysql:3306 --timeout=30" \
			-e DJANGO_SETTINGS_MODULE=settings.testmysql \
			--user $(CALLER_UID):$(CALLER_GID) \
			--workdir /src \
			--rm \
			--entrypoint tox \
				archivematica-tests \
					$(subst $(space), -e ,$(space)$(1)) \
					$(TOXARGS))
endef

create-volumes:  ## Create external data volumes.
	mkdir -p ${AM_PIPELINE_DATA}
	docker volume create \
		--opt type=none \
		--opt o=bind \
		--opt device=$(AM_PIPELINE_DATA) \
			am-pipeline-data
	mkdir -p ${SS_LOCATION_DATA}
	docker volume create \
		--opt type=none \
		--opt o=bind \
		--opt device=$(SS_LOCATION_DATA) \
			ss-location-data

build:  # Build Compose services.
	docker-compose build

bootstrap: bootstrap-storage-service bootstrap-dashboard-db bootstrap-dashboard-frontend  ## Full bootstrap.

bootstrap-storage-service:  ## Boostrap Storage Service (new database).
	docker-compose exec mysql mysql -hlocalhost -uroot -p12345 -e "\
		DROP DATABASE IF EXISTS SS; \
		CREATE DATABASE SS; \
		GRANT ALL ON SS.* TO 'archivematica'@'%' IDENTIFIED BY 'demo';"
	docker-compose run \
		--rm \
		--entrypoint /src/storage_service/manage.py \
			archivematica-storage-service \
				migrate --noinput
	docker-compose run \
		--rm \
		--entrypoint /src/storage_service/manage.py \
			archivematica-storage-service \
				create_user \
					--username="test" \
					--password="test" \
					--email="test@test.com" \
					--api-key="test" \
					--superuser
	# SS needs to be restarted so the local space is created.
	# See #303 (https://git.io/vNKlM) for more details.
	docker-compose restart archivematica-storage-service

makemigrations-ss:
	docker-compose run \
		--rm \
		--entrypoint /src/storage_service/manage.py \
			archivematica-storage-service \
				makemigrations

manage-dashboard:  ## Run Django /manage.py on Dashboard, suppling <command> [options] as value to ARG, e.g., `make manage-ss ARG=shell`
	docker-compose run \
		--rm \
		--entrypoint /src/src/dashboard/src/manage.py \
			archivematica-dashboard \
				$(ARG)

manage-ss:  ## Run Django /manage.py on Storage Service, suppling <command> [options] as value to ARG, e.g., `make manage-ss ARG='shell --help'`
	docker-compose run \
		--rm \
		--entrypoint /src/storage_service/manage.py \
			archivematica-storage-service \
				$(ARG)

bootstrap-dashboard-db:  ## Bootstrap Dashboard (new database).
	docker-compose exec mysql mysql -hlocalhost -uroot -p12345 -e "\
		DROP DATABASE IF EXISTS MCP; \
		CREATE DATABASE MCP; \
		GRANT ALL ON MCP.* TO 'archivematica'@'%' IDENTIFIED BY 'demo';"
	docker-compose run \
		--rm \
		--entrypoint /src/src/dashboard/src/manage.py \
			archivematica-dashboard \
				migrate --noinput
	docker-compose run \
		--rm \
		--entrypoint /src/src/dashboard/src/manage.py \
			archivematica-dashboard \
				install \
					--username="test" \
					--password="test" \
					--email="test@test.com" \
					--org-name="test" \
					--org-id="test" \
					--api-key="test" \
					--ss-url="http://archivematica-storage-service:8000" \
					--ss-user="test" \
					--ss-api-key="test" \
					--site-url="http://archivematica-dashboard:8000"

bootstrap-dashboard-frontend:  ## Build front-end assets.
	docker-compose run \
		-e HOME=/tmp/yarn-config \
		--rm \
		--no-deps \
		--user $(CALLER_UID):$(CALLER_GID) \
		--entrypoint yarn \
			archivematica-dashboard \
				--cwd=/src/src/dashboard/frontend install --frozen-lockfile

restart-am-services:  ## Restart Archivematica services: MCPServer, MCPClient, Dashboard and Storage Service.
	docker-compose restart archivematica-mcp-server
	docker-compose restart archivematica-mcp-client
	docker-compose restart archivematica-dashboard
	docker-compose restart archivematica-storage-service

compile-requirements-am:  ## Run pip-compile for Archivematica
	docker-compose run --workdir /src \
		-e XDG_CACHE_HOME=/tmp/pip-cache \
		--rm \
		--no-deps \
		--user $(CALLER_UID):$(CALLER_GID) \
		--entrypoint bash archivematica-mcp-server \
			-c "make pip-compile"

compile-requirements-ss:  ## Run pip-compile for Storage Service
	docker-compose run --workdir /src/requirements \
		-e XDG_CACHE_HOME=/tmp/pip-cache \
		--rm \
		--no-deps \
		--user $(CALLER_UID):$(CALLER_GID) \
		--entrypoint bash archivematica-storage-service \
			-c "make clean && make all"

db:  ## Connect to the MySQL server using the CLI.
	docker-compose exec mysql mysql -hlocalhost -uroot -p12345

flush: flush-shared-dir flush-search bootstrap restart-am-services  ## Delete ALL user data.

flush-shared-dir-mcp-configs:  ## Delete processing configurations - it restarts MCPServer.
	rm -f ${AM_PIPELINE_DATA}/sharedMicroServiceTasksConfigs/processingMCPConfigs/defaultProcessingMCP.xml
	rm -f ${AM_PIPELINE_DATA}/sharedMicroServiceTasksConfigs/processingMCPConfigs/automatedProcessingMCP.xml
	docker-compose restart archivematica-mcp-server

flush-shared-dir:  ## Delete contents of the shared directory data volume.
	rm -rf ${AM_PIPELINE_DATA}/*

flush-search:  ## Delete Elasticsearch indices.
	docker-compose exec archivematica-mcp-client curl -XDELETE "http://elasticsearch:9200/aips,aipfiles,transfers,transferfiles"

flush-logs:  ## Delete container logs - requires root privileges.
	@./helpers/flush-docker-logs.sh

define drop_db
	docker-compose exec mysql mysql -hlocalhost -uroot -p12345 -e 'DROP DATABASE IF EXISTS `$(1)`;'
endef

flush-test-dbs:
	@find $(AMDIR) -type f -name '*-test.db*' -delete
	$(call drop_db,DASHBOARDTEST)
	$(call drop_db,MCPCLIENTTEST)
	$(call drop_db,MCPSERVERTEST)
	$(call drop_db,SSTEST)
	$(call drop_db,test_DASHBOARDTEST)
	$(call drop_db,test_DASHBOARDTEST_archivematica-common)
	$(call drop_db,test_DASHBOARDTEST_dashboard)
	$(call drop_db,test_MCP)
	$(call drop_db,test_MCPCLIENTTEST)
	$(call drop_db,test_MCPCLIENTTEST_mcpclient)
	$(call drop_db,test_MCPSERVERTEST)
	$(call drop_db,test_MCPSERVERTEST_mcpserver)
	$(call drop_db,test_SS)
	$(call drop_db,test_SSTEST)
	$(call drop_db,test_SSTEST_storage-service)

test-build:  ## Build archivematica-tests image.
	$(call compose_tests,build archivematica-tests)

test-build-integration:  ## Build archivematica-tests image.
	$(call compose_tests,build mysql archivematica-tests)

__TOXENVS_ALL := mcpserver mcpclient mcpclient-ensure-no-mutable-globals dashboard storage-service archivematica-common
test-all: test-build  ## Run all tests. Use `make test-all TOXARGS=--parallel` to run them in parallel.
	$(call toxenvs,$(__TOXENVS_ALL))

test-all-integration: test-build-integration  ## Run all tests with MySQL. Use `make test-all TOXARGS=--parallel` to run them in parallel.
	$(call toxenvs_integration,$(__TOXENVS_ALL))

__TOXENVS_MCPSERVER := mcpserver
test-mcp-server: test-build  ## Run MCPServer tests. Use `make test-mcp-server TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs,$(__TOXENVS_MCPSERVER))

test-mcp-server-integration: test-build-integration  ## Run MCPServer tests using MySQL. Use `make test-mcp-server-integration TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs_integration,$(__TOXENVS_MCPSERVER))

__TOXENVS_MCPCLIENT = mcpclient mcpclient-ensure-no-mutable-globals
test-mcp-client: test-build  ## Run MCPClient tests. Use `make test-mcp-client TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs,$(__TOXENVS_MCPCLIENT))

test-mcp-client-integration: test-build-integration  ## Run MCPClient tests using MySQL. Use `make test-mcp-client-integration TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs_integration,$(__TOXENVS_MCPCLIENT))

__TOXENVS_DASHBOARD = dashboard
test-dashboard: test-build  ## Run Dashboard tests. Use `make test-dashboard TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs,$(__TOXENVS_DASHBOARD))

test-dashboard-integration: test-build-integration  ## Run Dashboard tests using MySQL. Use `make test-dashboard-integration TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs_integration,$(__TOXENVS_DASHBOARD))

__TOXENVS_STORAGE_SERVICE = storage-service
test-storage-service: test-build  ## Run Storage Service tests. Use `make test-storage-service TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs,$(__TOXENVS_STORAGE_SERVICE))

test-storage-service-integration:  ## Run Storage Service tests (including integration tests) using MySQL.
	$(CURDIR)/submodules/archivematica-storage-service/integration/run.sh

__TOXENVS_ARCHIVEMATICA_COMMON = archivematica-common
test-archivematica-common: test-build  ## Run Archivematica Common tests. Use `make test-archivematica-common TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs,$(__TOXENVS_ARCHIVEMATICA_COMMON))

test-archivematica-common-integration: test-build-integration  ## Run Archivematica Common tests using MySQL. Use `make test-archivematica-common-integration TOXARGS=-- --reuse-db` to keep the database between runs.
	$(call toxenvs_integration,$(__TOXENVS_ARCHIVEMATICA_COMMON))

__TOXENVS_CHECKFORMIGRATIONS = checkformigrations-dashboard checkformigrations-storage-service
test-checkformigrations: test-build  ## Check there are no pending migrations.
	$(call toxenvs,$(__TOXENVS_CHECKFORMIGRATIONS))

__TOXENVS_LINTING = linting
test-linting: test-build  ## Check linting.
	$(call toxenvs,$(__TOXENVS_LINTING))

test-at-build:  ## AMAUAT: build image.
	$(call compose_amauat, \
		build archivematica-acceptance-tests)

test-at-check: test-at-build  ## AMAUAT: test browsers.
	$(call compose_amauat, \
		run --rm --no-deps archivematica-acceptance-tests /home/archivematica/acceptance-tests/simplebrowsertest.py)

define AT_HELP

   Archivematica acceptance tests (Listing).

   The most effective way to run these tests is to run them by tag. For
   example:

      $ make test-at-behave TAGS=aip-encrypt BROWSER=Firefox
      $ make test-at-behave TAGS=black-box

   Commonly used acceptance tests in the Archivematica suite:

      * aip-encrypt        :Tests the encryption of AIPs.
      * aip-encrypt-mirror :Tests the replication of encrypted AIPs.
      * black-box          :Test Archivematica without Selenium web-driver.
      * icc                :Conformance check feature on ingest.
      * ipc                :Policy check feature on ingest.
      * picc               :Policy check feature for preservation derivatives.
      * mo-aip-reingest    :Metadata-only reingest.
      * tpc                :Policy check feature on transfer.
      * uuids-dirs         :Tests whether UUIDs are assigned to AIP sub-DIRs.

endef

export AT_HELP
test-at-help:  ## AMAUAT: list commonly used acceptance test tags.
	@echo "$$AT_HELP"

TAGS ?= mo-aip-reingest
BROWSER ?= Firefox
test-at-behave: test-at-build  ## AMAUAT: run behave, default is `make test-at-behave TAGS=mo-aip-reingest BROWSER=Firefox`.
	$(call compose_amauat, \
		run --rm -e HEADLESS=1 --no-deps archivematica-acceptance-tests /usr/local/bin/behave \
			--tags=$(TAGS) --no-skipped -v --stop \
			-D driver_name=$(BROWSER) \
			-D ssh_accessible=no \
			-D am_url=http://nginx/ \
			-D am_username=test \
			-D am_password=test \
			-D am_api_key=test \
			-D am_version=1.8 \
			-D ss_url=http://nginx:8000/ \
			-D ss_username=test \
			-D ss_password=test \
			-D ss_api_key=test \
			-D transfer_source_path=archivematica/archivematica-sampledata/TestTransfers/acceptance-tests \
			-D home=archivematica)

test-at-black-box: TAGS=black-box  ## AMAUAT: run the black-box automation tests.
test-at-black-box: test-at-behave

test-frontend:  ## Run Dashboard JS tests.
	docker build \
		-t archivematica-dashboard-testing \
		-f $(CURDIR)/Dockerfile \
		--build-arg TARGET=archivematica-dashboard-testing \
			../
	docker run \
		--rm \
		--volume "$(SRCDIR)/dashboard/frontend:/src/src/dashboard/frontend" \
			archivematica-dashboard-testing

help:  ## Print this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
