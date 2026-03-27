DOCKER_COMPOSE_DEV = docker-compose
DOCKER_COMPOSE_CI = docker-compose -f docker-compose.yml -f docker-compose.ci.yml
DOCKER_COMPOSE = $(DOCKER_COMPOSE_DEV)

VENV = .venv
PYTHON = uv run python

DEV_RUN = $(DOCKER_COMPOSE) run --name "$(RUN_NAME)" --rm sciencebeam-judge-dev

MOUNT = --volume="$$PWD/example-data:/example-data"

RUN_NAME =
JUDGE_SERVICE = sciencebeam-judge
RUN = $(DOCKER_COMPOSE) run $(MOUNT) --name "$(RUN_NAME)" --rm $(JUDGE_SERVICE)

JUPYTER_MOUNT = --volume="$$PWD/example-data:/home/jovyan/sciencebeam-judge/example-data"
JUPYTER_RUN = $(DOCKER_COMPOSE) run $(JUPYTER_MOUNT) --name "$(RUN_NAME)" --rm sciencebeam-judge-jupyter


PYTEST_ARGS =
EVALUATE_ARGS =
TOOL =
EVALUATION_RESULTS_OUTPUT_PATH = /example-data/pmc-sample-1943-cc-by-subset-results/$(TOOL)/evaluation-results
NOTEBOOK_OUTPUT_FILE =
NO_BUILD =

EXAMPLE_DATA_EXPECTED_BASE_PATH = ./example-data/pmc-sample-1943-cc-by-subset
EXAMPLE_DATA_ACTUAL_BASE_PATH = ./example-data/pmc-sample-1943-cc-by-subset-results/grobid-tei

PROFILE_ARGS =


.PHONY: build


venv-clean:
	@if [ -d "$(VENV)" ]; then \
		rm -rf "$(VENV)"; \
	fi


venv-create:
	uv venv "$(VENV)"


dev-install:
	uv sync --frozen --all-groups


dev-venv: venv-create dev-install


dev-flake8:
	$(PYTHON) -m flake8 sciencebeam_judge tests


dev-pylint:
	$(PYTHON) -m pylint sciencebeam_judge tests


dev-mypy:
	$(PYTHON) -m mypy --ignore-missing-imports --no-site-packages sciencebeam_judge tests


dev-lint: dev-flake8 dev-pylint dev-mypy


dev-pytest:
	$(PYTHON) -m pytest -p no:cacheprovider $(ARGS)


dev-watch:
	$(PYTHON) -m pytest_watch --ext=.py,.conf -- -p no:cacheprovider -p no:warnings $(ARGS)


dev-test: dev-lint dev-pytest


.dev-update-example-data-results:
	$(PYTHON) -m sciencebeam_judge.evaluation_pipeline \
		--target-file-list $(EXAMPLE_DATA_EXPECTED_BASE_PATH)/file-list.tsv \
		--target-file-column=xml_url \
		--prediction-file-list ./example-data/pmc-sample-1943-cc-by-subset-results/$(TOOL)/file-list.lst \
		--output-path $(EVALUATION_RESULTS_OUTPUT_PATH) \
		--sequential \
		$(EVALUATE_ARGS)


dev-update-example-data-results-cermine:
	$(MAKE) TOOL=cermine \
		EVALUATION_RESULTS_OUTPUT_PATH=./example-data/pmc-sample-1943-cc-by-subset-results/cermine/evaluation-results \
		.dev-update-example-data-results


dev-update-example-data-results-cermine-temp:
	$(MAKE) TOOL=cermine EVALUATION_RESULTS_OUTPUT_PATH=/tmp .dev-update-example-data-results


dev-update-example-data-results-grobid-tei:
	$(MAKE) TOOL=grobid-tei \
		EVALUATION_RESULTS_OUTPUT_PATH=./example-data/pmc-sample-1943-cc-by-subset-results/grobid-tei/evaluation-results \
		.dev-update-example-data-results


dev-update-example-data-results-grobid-tei-temp:
	$(MAKE) TOOL=grobid-tei EVALUATION_RESULTS_OUTPUT_PATH=/tmp .dev-update-example-data-results


dev-update-example-data-results: \
	dev-update-example-data-results-cermine dev-update-example-data-results-grobid-tei


dev-test-run-evaluation: \
	dev-update-example-data-results-cermine-temp dev-update-example-data-results-grobid-tei-temp


dev-update-example-data-notebooks-summary:
	uv run bash scripts/jupyter/update-notebook-and-check-no-errors.sh \
		notebooks/conversion-results-summary.ipynb "$(NOTEBOOK_OUTPUT_FILE)"


dev-update-example-data-notebooks-details:
	uv run bash scripts/jupyter/update-notebook-and-check-no-errors.sh \
		notebooks/conversion-results-details.ipynb "$(NOTEBOOK_OUTPUT_FILE)"


dev-update-example-data-notebooks: \
	dev-update-example-data-notebooks-summary dev-update-example-data-notebooks-details


dev-update-example-data-notebooks-temp:
	$(MAKE) NOTEBOOK_OUTPUT_FILE="/tmp/dummy.ipynb" dev-update-example-data-notebooks


dev-test-evaluate-and-update-notebooks: \
	dev-update-example-data-results dev-update-example-data-notebooks-temp


dev-distance-matching-profile:
	$(PYTHON) -m tests.utils.distance_matching_profile


dev-distance-matching-profile-example-1:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Anaesthesiol_Scand_2011_Jan_55(1)_39-45/aas0055-0039.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Anaesthesiol_Scand_2011_Jan_55(1)_39-45/aas0055-0039.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-2:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Crystallogr_D_Biol_Crystallogr_2011_May_1_67(Pt_5)_463-470/d-67-00463.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Crystallogr_D_Biol_Crystallogr_2011_May_1_67(Pt_5)_463-470/d-67-00463.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-3:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Crystallogr_Sect_E_Struct_Rep_Online_2011_May_7_67(Pt_6)_o1363-o1364/e-67-o1363.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Crystallogr_Sect_E_Struct_Rep_Online_2011_May_7_67(Pt_6)_o1363-o1364/e-67-o1363.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-4:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Crystallogr_Sect_F_Struct_Biol_Cryst_Commun_2011_Feb_23_67(Pt_3)_344-348/f-67-00344.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Crystallogr_Sect_F_Struct_Biol_Cryst_Commun_2011_Feb_23_67(Pt_3)_344-348/f-67-00344.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-5:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Obstet_Gynecol_Scand_2010_Jul_5_89(7)_975-979/sobs89-975.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Obstet_Gynecol_Scand_2010_Jul_5_89(7)_975-979/sobs89-975.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-6:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Oncol_2011_Jun_16_50(5)_621-629/sonc50-621.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Oncol_2011_Jun_16_50(5)_621-629/sonc50-621.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-7:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Orthop_2010_Jun_21_81(3)_405-406/ORT-1745-3674-81-405.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Orthop_2010_Jun_21_81(3)_405-406/ORT-1745-3674-81-405.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-8:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Otolaryngol_2011_May_3_131(5)_469-473/soto131-469.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Otolaryngol_2011_May_3_131(5)_469-473/soto131-469.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-9:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Paediatr_2011_May_100(5)_653-660/apa0100-0653.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Paediatr_2011_May_100(5)_653-660/apa0100-0653.xml" \
		$(PROFILE_ARGS)


dev-distance-matching-profile-example-10:
	$(PYTHON) -m tests.utils.distance_matching_profile \
		--expected-xml="$(EXAMPLE_DATA_EXPECTED_BASE_PATH)/Acta_Physiol_(Oxf)_2011_Jul_202(3)_379-385/apha0202-0379.nxml" \
		--actual-xml="$(EXAMPLE_DATA_ACTUAL_BASE_PATH)/Acta_Physiol_(Oxf)_2011_Jul_202(3)_379-385/apha0202-0379.xml" \
		$(PROFILE_ARGS)


build:
	if [ "$(NO_BUILD)" != "y" ]; then \
		$(DOCKER_COMPOSE) build; \
	fi


build-judge:
	@if [ "$(NO_BUILD)" != "y" ]; then \
		$(DOCKER_COMPOSE) build sciencebeam-judge; \
	fi


build-dev:
	if [ "$(NO_BUILD)" != "y" ]; then \
		$(DOCKER_COMPOSE) build sciencebeam-judge-dev; \
	fi


test: build-dev
	$(DEV_RUN) ./project_tests.sh


watch: build-dev
	$(DEV_RUN) pytest-watch -- $(PYTEST_ARGS)


.update-example-data-results:
	$(RUN) python -m sciencebeam_judge.evaluation_pipeline \
		--target-file-list /example-data/pmc-sample-1943-cc-by-subset/file-list.tsv \
		--target-file-column=xml_url \
		--prediction-file-list /example-data/pmc-sample-1943-cc-by-subset-results/$(TOOL)/file-list.lst \
		--output-path $(EVALUATION_RESULTS_OUTPUT_PATH) \
		--sequential \
		$(EVALUATE_ARGS)


update-example-data-results-cermine:
	$(MAKE) TOOL=cermine .update-example-data-results


update-example-data-results-cermine-temp:
	$(MAKE) EVALUATION_RESULTS_OUTPUT_PATH=/tmp update-example-data-results-cermine


update-example-data-results-grobid-tei:
	$(MAKE) TOOL=grobid-tei .update-example-data-results


update-example-data-results-grobid-tei-temp:
	$(MAKE) EVALUATION_RESULTS_OUTPUT_PATH=/tmp update-example-data-results-grobid-tei


update-example-data-results: \
	update-example-data-results-cermine update-example-data-results-grobid-tei 


update-example-data-results-temp: \
	update-example-data-results-cermine-temp update-example-data-results-grobid-tei-temp


update-example-data-notebooks-summary:
	$(JUPYTER_RUN) update-notebook-and-check-no-errors.sh \
		conversion-results-summary.ipynb "$(NOTEBOOK_OUTPUT_FILE)"


update-example-data-notebooks-details:
	$(JUPYTER_RUN) update-notebook-and-check-no-errors.sh \
		conversion-results-details.ipynb "$(NOTEBOOK_OUTPUT_FILE)"


update-example-data-notebooks: \
	update-example-data-notebooks-summary update-example-data-notebooks-details


update-example-data-notebooks-temp:
	$(MAKE) NOTEBOOK_OUTPUT_FILE="/tmp/dummy.ipynb" update-example-data-notebooks


jupyter-build:
	if [ "$(NO_BUILD)" != "y" ]; then \
		$(DOCKER_COMPOSE) build sciencebeam-judge-jupyter; \
	fi


jupyter-shell: jupyter-build
	$(DOCKER_COMPOSE) run --rm sciencebeam-judge-jupyter bash


jupyter-start: jupyter-build
	$(DOCKER_COMPOSE) up -d sciencebeam-judge-jupyter


jupyter-logs:
	$(DOCKER_COMPOSE) logs -f sciencebeam-judge-jupyter


jupyter-stop:
	$(DOCKER_COMPOSE) down


ci-build-all:
	$(DOCKER_COMPOSE_CI) build --parallel


ci-test:
	$(MAKE) DOCKER_COMPOSE="$(DOCKER_COMPOSE_CI)" \
		RUN_NAME="ci-test" \
		test


ci-test-run-evaluation:
	$(MAKE) dev-test-run-evaluation


ci-test-evaluate-and-update-notebooks:
	$(MAKE) dev-test-evaluate-and-update-notebooks


ci-clean:
	$(DOCKER_COMPOSE_CI) down -v
