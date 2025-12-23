# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant
technical decisions made during the development of Universe Screener.

## What is an ADR?

An ADR is a short document that captures an important architectural decision
along with its context and consequences.

## ADR Template

```markdown
# ADR-XXX: Title

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-YYY

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the decision that we're proposing?

## Consequences
What becomes easier or harder because of this decision?
```

## Existing Decisions

### Accepted

- **ADR-001**: Dependency Injection via Constructor
  - All external dependencies injected, not created internally
  - Enables testing with mocks

- **ADR-002**: Batch Loading Strategy for Performance
  - Load all data upfront, filter in-memory
  - Avoids N+1 query problem

- **ADR-003**: Strategy Pattern for Asset-Class Specific Logic
  - LiquidityFilter uses different strategies per asset class
  - Extensible to new asset classes

### Pending

- **ADR-004**: Error Handling Approach (Retry + Circuit Breaker)
- **ADR-005**: Observability Stack (structlog + OpenMetrics)
- **ADR-006**: Cache Strategy (TTL vs Event-Based vs Versioned)
- **ADR-007**: Async vs Sync (Start Sync, Migrate Later)

### Future

- **ADR-008**: Plugin Architecture (Registry Pattern)

## Creating New ADRs

1. Copy the template above
2. Number sequentially (ADR-XXX)
3. Fill in all sections
4. Add to this README's index
5. Submit with related code changes

