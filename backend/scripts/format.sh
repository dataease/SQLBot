#!/bin/sh -e
set -x

ruff check apps scripts common --fix
ruff format apps scripts common
