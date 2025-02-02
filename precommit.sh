#!/bin/bash
poetry run black toggle_display_input tests
poetry run pytest -v
