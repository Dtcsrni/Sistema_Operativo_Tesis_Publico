# build_runner/__init__.py
"""build_runner — Sistema de build modular e incremental para el proyecto SIOT.

Módulos:
  registry  — Catálogo de pasos con metadatos (grupo, tags, watch, soft_fail)
  cache     — Fingerprints SHA-256 para builds incrementales
  runner    — Motor de ejecución, StepReport, perfiles JSON

Uso desde build_all.py:
  from build_runner import registry, cache, runner
"""
