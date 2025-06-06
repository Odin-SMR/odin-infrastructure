DEVELOPER_ENV := requirements-dev.in
PIP_COMPILE := pip-compile -q --resolver=backtracking
CONSTRAINTS_ENV := $(addsuffix .txt, $(basename $(DEVELOPER_ENV)))

MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(patsubst %/,%,$(dir $(MKFILE_PATH)))
SOURCES := $(filter-out $(DEVELOPER_ENV), $(shell find . -name 'requirements*.in'))

$(CONSTRAINTS_ENV): $(SOURCES)
	$(PIP_COMPILE) --strip-extras -o "$@" $(SOURCES) "$(DEVELOPER_ENV)"


%.txt: %.in
	$(PIP_COMPILE) --no-strip-extras --no-annotate \
		--constraint="$(CURRENT_DIR)/$(CONSTRAINTS_ENV)" \
		-o "$@" "$<"

all: $(CONSTRAINTS_ENV) $(addsuffix .txt, $(basename $(SOURCES)))

update: clean all

clean:
	rm -f "$(CONSTRAINTS_ENV)" $(addsuffix .txt, $(basename $(SOURCES)))


.PHONY: all clean update

