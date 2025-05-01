# Makefile for GPKG Conversion Project

# Variables
VENV_NAME = .venv
PYTHON = python3
PIP = pip
REQUIREMENTS = requirements.txt
SRC_DIR = .
MAIN_SCRIPT = gpkg_converter.py

# Default target
.PHONY: all
all: venv install

# Create virtual environment
.PHONY: venv
venv:
	$(PYTHON) -m venv $(VENV_NAME)
	@echo "Virtual environment created: $(VENV_NAME)"

# Install dependencies
.PHONY: install
install: venv
ifeq ($(OS),Windows_NT)
	$(VENV_NAME)\Scripts\pip install -r $(REQUIREMENTS)
else
	$(VENV_NAME)/bin/pip install -r $(REQUIREMENTS)
endif
	@echo "Dependencies installed"

# Run the script
.PHONY: run
run:
ifeq ($(OS),Windows_NT)
	$(VENV_NAME)\Scripts\python $(SRC_DIR)/$(MAIN_SCRIPT) $(ARGS)
else
	$(VENV_NAME)/bin/python $(SRC_DIR)/$(MAIN_SCRIPT) $(ARGS)
endif

# Clean up
.PHONY: clean
clean:
	rm -rf $(VENV_NAME)
	rm -rf __pycache__
	rm -rf *.png
	rm -rf *.geojson
	@echo "Cleaned up environment and generated files"

# Help
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make          - Create virtual environment and install dependencies"
	@echo "  make venv     - Create virtual environment only"
	@echo "  make install  - Install dependencies in virtual environment"
	@echo "  make run      - Run the main script (use ARGS='path/to/your.gpkg' to specify file)"
	@echo "  make clean    - Remove virtual environment and generated files"
	@echo "  make help     - Show this help message"