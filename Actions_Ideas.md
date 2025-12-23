# Actions & Ideas - Universe Screener

**Stand:** 2024-12-23
**Maturity:** DEVELOPMENT
**Version:** 0.3.0

---

## 🔴 Offene TODOs (aus Session)

### 1. SnapshotManager - Provider Integration erweitern
**Priorität:** STABILIZATION
**Datei:** `src/universe_screener/pipeline/screening_pipeline.py`

Der SnapshotManager erstellt eine `snapshot_id`, aber diese wird nicht an den Provider weitergegeben. Für echte Point-in-Time-Konsistenz müsste:
- `UniverseProviderProtocol` um `snapshot_id` Parameter erweitert werden
- Provider müsste gegen versionierte Datenbank abfragen

**Aktuell:** Snapshot-ID wird nur in Metadata gespeichert (Audit-Trail).

```python
# TODO: Extend provider protocol
def get_assets(
    self, 
    date: datetime, 
    asset_class: AssetClass,
    snapshot_id: Optional[str] = None,  # NEU
) -> List[Asset]:
```

---

### 2. Type Aliases konsequent nutzen
**Priorität:** LOW
**Datei:** `src/universe_screener/domain/value_objects.py`

Type Aliases wurden definiert aber noch nicht überall eingesetzt:
- `MarketDataDict = Dict[str, List[MarketData]]`
- `MetadataDict = Dict[str, Dict[str, Any]]`
- `QualityMetricsDict = Dict[str, QualityMetrics]`

**Status:** In `screening_pipeline.py` bereits verwendet, andere Module folgen bei Bedarf.

---

### 3. datetime vs date Konsistenz
**Priorität:** MEDIUM
**Datei:** `.cursorrules` (bereits dokumentiert)

Regel hinzugefügt:
- Alle temporalen Werte als `datetime` (nicht `date`)
- Ausnahme: `listing_date` und `delisting_date` in Asset Entity

**Umsetzung:** `date.date()` Konvertierung nur an Entity-Grenzen.

---

## 🟡 Coverage-Lücken (Low Priority)

### Interface Protocol Files (0% Coverage)
**Dateien:**
- `interfaces/audit_logger.py`
- `interfaces/filter_stage.py`
- `interfaces/health_monitor.py`
- `interfaces/metrics_collector.py`
- `interfaces/universe_provider.py`

**Grund:** Abstrakte Protokolle ohne Implementierung.
**Aktion:** Akzeptabel - Protokolle sind nur Type Hints.

### Pipeline Uncovered Paths (~77% Coverage)
**Datei:** `src/universe_screener/pipeline/screening_pipeline.py`

Uncovered: Optionale Dependency-Pfade (wenn error_handler, validators nicht injected).
**Aktion:** Integration-Tests mit allen optionalen Dependencies hinzufügen.

---

## 🔵 Nächste Phasen (Roadmap)

### Phase 3: Caching Layer (noch nicht gestartet)
Gemäß `docs/architecture/04_implementation_roadmap.md`:
- CacheManager implementieren
- TTL-basierte Cache-Invalidierung
- Provider-Cache-Integration

### Phase 4: Plugin Architecture (noch nicht gestartet)
- FilterRegistry für dynamische Filter
- Config-driven Filter-Aktivierung
- Custom Filter Support

---

## 💡 Ideen für später

### 1. Prometheus Metrics Export
`requirements.txt` enthält bereits (auskommentiert):
```
# prometheus-client>=0.19.0  # Metrics export
```

ObservabilityManager könnte Prometheus-Format exportieren.

### 2. Structured Logging JSON Output
structlog ist installiert. Für Production:
```python
manager = ObservabilityManager(use_json=True)
```

### 3. Backtest-Integration
SnapshotManager könnte für Backtesting erweitert werden:
- Historische Snapshots laden
- Replay von Screening-Runs

### 4. CLI Interface
Entry Point für Command-Line-Nutzung:
```bash
universe-screener screen --date 2024-12-15 --asset-class STOCK
```

---

## ✅ Abgeschlossen (Session 2024-12-23)

- [x] Phase 0: Foundation (Entities, Filters, Pipeline)
- [x] Phase 1: Resilience Layer (ErrorHandler, Validators)
- [x] Phase 2: Observability Layer (ObservabilityManager, HealthMonitor, SnapshotManager, VersionManager)
- [x] 131 Tests (Unit, Integration, Performance)
- [x] 89.34% Code Coverage
- [x] Performance: 5000 Assets in 0.09s

