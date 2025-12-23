"""
Pipeline Package - Orchestration and Data Management.

This package contains the core orchestration logic for the screening
pipeline and the in-memory data container.

Components:
    - ScreeningPipeline: Main orchestrator coordinating all stages
    - DataContext: In-memory container for loaded data

The pipeline is responsible for:
    - Validating screening requests
    - Orchestrating data loading
    - Executing filter stages in sequence
    - Collecting metrics and audit trail
    - Generating the final ScreeningResult

Design Principles:
    - All dependencies injected via constructor
    - Stateless operation (state in DataContext)
    - Clear separation of concerns
"""

# TODO: Implement - Export pipeline classes after implementation

