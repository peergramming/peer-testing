#!/bin/sh
# Junit testing template file
# $1 = tmp directory
# $2 = lib directory
# Exit the script with $? so that the java exit code is recorded
cp $2/junit.jar $2/hamcrest.jar $1
javac -cp .:junit.jar:hamcrest.jar *.java
java -cp .:junit.jar:hamcrest.jar org.junit.runner.JUnitCore MyTest
exit $?
