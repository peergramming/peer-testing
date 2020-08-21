#!/bin/sh
# Python unit test template file
# Exit the script with $? so that the python exit code is recorded
# $1 = tmp directory
# $2 = lib directory
python3 -m unittest discover -p "*.py"
exit $?