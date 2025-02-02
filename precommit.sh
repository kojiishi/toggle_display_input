#!/bin/bash
if [[ -z "$VIRTUAL_ENV" ]]; then
  echo "Activating Poetry environment and rerunning..."
  poetry run "$SHELL" "$0" "$@"
  exit $?
fi
black toggle_display_input tests
pytest -v
