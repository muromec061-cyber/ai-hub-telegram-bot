#!/usr/bin/env bash
# Run database migrations
set -e
alembic upgrade head
