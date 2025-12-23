"""
Interfaces Layer - Abstract Protocols for Dependencies.

This package defines the abstract interfaces (using typing.Protocol) for all
external dependencies. Following the Dependency Inversion Principle, high-level
modules depend on these abstractions, not on concrete implementations.

Protocols:
    - UniverseProvider: Data access abstraction
    - FilterStage: Base protocol for filter stages
    - AuditLogger: Logging abstraction for audit trail
    - MetricsCollector: Performance metrics abstraction
    - HealthMonitor: System health checks

Design Principles:
    - Use typing.Protocol (not ABC) for Pythonic interfaces
    - Interface Segregation: Small, focused interfaces
    - All methods have clear contracts in docstrings
    - No implementation details leak into interfaces
"""

# TODO: Implement - Export protocols after implementation

