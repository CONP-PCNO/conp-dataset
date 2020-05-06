# CONP dataset - Test suite

[![CircleCI](https://circleci.com/gh/CONP-PCNO/conp-dataset.svg?style=shield)](https://circleci.com/gh/CONP-PCNO/conp-dataset)

## Executing the test

### Dependencies

<!-- Git-annex -->
<!-- Python requirements -->

### Containerized dependencies

<!-- Link -->
<!-- Steps to buidl python dependencies -->

## Test suite Structure

### Code base

<!-- Utility functions -->
<!-- Template -->
<!-- Test generation -->

### Circle CI

<!-- Workflow structure -->
<!-- Level of parallism -->

# Life of a dataset test

## Test creation

### Minimal testing

<!-- Motivation (Only test required dataset) -->
<!-- Describe implementation and consequences-->

#### Whitelist Exact

<!-- Exact whitelist files -->

#### Whitelist

<!-- Whitelist files -->

## Set up

<!-- Motivation (Avoid global test failure + reduce execution time) -->
<!-- Autouse fixture -->

## Dataset validation

### Has `README.md`

<!-- Motivation -->
<!-- Contains file -->

### Has a valid `DATS.json` file

<!-- Motivation -->
<!-- Contains file -->
<!-- DATS validator -->

### Datalad Get

<!-- Motivation -->
<!-- authentication (Secret limitations) (Section on authenticated dataset) -->
<!-- n files form sub-sample to avoid timeout -->
<!-- datalad get %FILENAME -->

### Files Integrity

<!-- Motivation -->
<!-- git-annex fsck on all files -->

## Monitoring

### Motivation

<!-- Dataset still work -->
<!-- Last time dataset worked -->
<!-- Integration in CONP-Portal -->

# Authenticated Dataset

<!-- What should be done prior the tests -->

## Secret creation

<!-- useing project_name2env -->
<!-- Add them into CircleCI/TravisCI -->

## Limitations with secrets

<!-- Limitations -->
<!-- Work around by setting up secret in your personnal CircleCI -->

# Implementation keypoints

## Flaky test

<!-- Motivation () -->
<!-- Maximum retry -->
<!-- Lock datalad install -->
<!-- Delay between retrys -->

## Empty dataset

<!-- No file in annex -->

## Timeout

<!-- CircleCI timeout -->
<!-- Download timeout -->

## Size of annexed file

<!-- Motivation -->
<!-- INFINITY if not able to retrieve -->
