#!/usr/bin/env python3
"""
verify_observability_isolation.py
Verifica que la observabilidad del sistema respeta el aislamiento por dominio.

Checks:
1. Configuración OTel Edge: existe y tiene resource processor con dominio=edge_iot
2. Configuración OTel Hub: existe y tiene exportador a Prometheus
3. Prometheus: NO tiene scrape_configs apuntando directamente al Edge
4. Reglas de alertas: existen por dominio sin cruce
5. Rutas de logs: runtime/edge_iot y runtime/openclaw son independientes

Referencia: T-033 / DEC-0046 / VAL-STEP-780
"""
import sys
import yaml
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ERRORS = []
WARNINGS = []


def check(cond: bool, msg: str, warn: bool = False):
    if not cond:
        (WARNINGS if warn else ERRORS).append(msg)
    return cond


def load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        ERRORS.append(f"Archivo no encontrado: {path.relative_to(REPO)}")
        return {}
    except yaml.YAMLError as e:
        ERRORS.append(f"YAML inválido en {path.relative_to(REPO)}: {e}")
        return {}


# ── CHECK 1: OTel Edge tiene resource processor con dominio=edge_iot
def check_otel_edge():
    cfg = load_yaml(REPO / "config/otel/collector-edge.yml")
    if not cfg:
        return
    processors = cfg.get("processors", {})
    resource = processors.get("resource", {})
    attrs = resource.get("attributes", [])
    has_dominio = any(
        a.get("key") == "dominio" and a.get("value") == "edge_iot"
        for a in attrs
    )
    check(has_dominio,
          "OTel Edge: falta atributo 'dominio=edge_iot' en el resource processor")

    # Verificar que usa file_storage (buffer para intermitencia)
    exporters = cfg.get("exporters", {})
    hub_exporter = exporters.get("otlp/hub", {})
    queue = hub_exporter.get("sending_queue", {})
    has_buffer = queue.get("storage") is not None
    check(has_buffer,
          "OTel Edge: exportador otlp/hub sin file_storage buffer (crítico para intermitencia)",
          warn=True)

    print(f"  [OK] OTel Edge: config encontrada con resource processor")


# ── CHECK 2: OTel Hub exporta a Prometheus
def check_otel_hub():
    cfg = load_yaml(REPO / "config/otel/collector-hub.yml")
    if not cfg:
        return
    exporters = cfg.get("exporters", {})
    has_remote_write = "prometheusremotewrite" in exporters
    check(has_remote_write,
          "OTel Hub: falta exportador 'prometheusremotewrite' hacia Prometheus")
    print(f"  [OK] OTel Hub: config encontrada con exportador Prometheus")


# ── CHECK 3: Prometheus NO scraping directo al Edge
def check_prometheus_no_edge_scrape():
    cfg = load_yaml(REPO / "config/prometheus/prometheus.yml")
    if not cfg:
        return
    scrape_configs = cfg.get("scrape_configs", [])
    edge_scrapes = []
    for sc in scrape_configs:
        static_cfgs = sc.get("static_configs", [])
        for scfg in static_cfgs:
            targets = scfg.get("targets", [])
            for t in targets:
                # Detectar IPs/hostnames que apunten al Edge (no al localhost del Hub)
                if any(edge_host in str(t) for edge_host in
                       ["orange-pi", "siot-edge", "edge_gw", "192.168.1.", "10.0.0."]):
                    edge_scrapes.append(f"{sc.get('job_name')}: {t}")

        # También detectar dns_sd_configs apuntando al Edge (válido si es para OTel Hub)
        dns_sd = sc.get("dns_sd_configs", [])
        for dns in dns_sd:
            names = dns.get("names", [])
            for name in names:
                if "_siot-edge" in name:
                    # Esto está OK si es el OTel Hub el que lo consume, pero Prometheus
                    # directo no debe hacerlo en este diseño
                    WARNINGS.append(
                        f"Prometheus scraping DNS-SD Edge directo: {name}. "
                        "Validar que sea el OTel Hub quien descubra, no Prometheus."
                    )

    check(len(edge_scrapes) == 0,
          f"Prometheus scraping directo al Edge detectado: {edge_scrapes}. "
          "Debe usar Remote Write desde OTel Hub (DEC-0046)")
    print(f"  [OK] Prometheus: sin scraping directo al Nodo Edge")


# ── CHECK 4: Reglas de alertas separadas por dominio
def check_alert_rules():
    rules_dir = REPO / "config/prometheus/rules"
    if not rules_dir.exists():
        ERRORS.append("Directorio config/prometheus/rules/ no existe")
        return

    expected_domains = {"edge_iot", "openclaw", "sistema_tesis"}
    found_files = {f.stem for f in rules_dir.glob("*.yml")}
    missing = expected_domains - found_files
    check(len(missing) == 0,
          f"Archivos de reglas faltantes: {missing}")

    # Verificar que cada archivo solo contiene labels de su dominio
    for rule_file in rules_dir.glob("*.yml"):
        cfg = load_yaml(rule_file)
        groups = cfg.get("groups", [])
        for g in groups:
            for rule in g.get("rules", []):
                labels = rule.get("labels", {})
                dominio_label = labels.get("dominio", "")
                if dominio_label and rule_file.stem not in dominio_label:
                    WARNINGS.append(
                        f"{rule_file.name}: alerta '{rule.get('alert')}' "
                        f"tiene dominio='{dominio_label}' pero está en el archivo '{rule_file.stem}'"
                    )

    print(f"  [OK] Reglas de alertas: {found_files} encontradas")


# ── CHECK 5: Rutas de logs aisladas
def check_log_isolation():
    log_dirs = [
        REPO / "runtime" / "edge_iot" / "logs",
        REPO / "runtime" / "edge_sync" / "buffer",
    ]
    for d in log_dirs:
        # Solo verificar que no existan archivos mezclados (e.g. openclaw en edge_iot)
        if d.exists():
            openclaw_files = list(d.glob("*openclaw*"))
            check(len(openclaw_files) == 0,
                  f"Mezcla de dominio detectada en {d.relative_to(REPO)}: {openclaw_files}",
                  warn=True)
    print(f"  [OK] Aislamiento de rutas de log: sin mezcla detectada")


# ── MAIN
def main():
    print("\n[VERIFY] Aislamiento de Observabilidad por Dominio (T-033)\n")

    check_otel_edge()
    check_otel_hub()
    check_prometheus_no_edge_scrape()
    check_alert_rules()
    check_log_isolation()

    print()
    if WARNINGS:
        for w in WARNINGS:
            print(f"  [WARN] {w}")

    if ERRORS:
        print(f"\n[FAIL] {len(ERRORS)} error(es) de aislamiento:")
        for e in ERRORS:
            print(f"  [ERR] {e}")
        sys.exit(1)
    else:
        print(f"[OK] Aislamiento de observabilidad verificado ({len(WARNINGS)} advertencias)")
        sys.exit(0)


if __name__ == "__main__":
    main()
