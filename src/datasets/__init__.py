"""Real-dataset loaders for MAAT.

Each loader returns ``(items, adapters)`` where:
  * ``items`` is a list of ``{"detector", "label", "native", "source"}`` dicts,
    the same shape the synthetic generator (``nlip_soc.generate_alerts``) produces,
    so the E1/E2/E3 harness runs unchanged.
  * ``adapters`` maps a detector name to a function ``native -> canonical OCSF event``.

Loaders:
  * ``ait_ads``  -- AIT Alert Data Set (real Wazuh, Suricata, AMiner alerts).
  * ``guide``    -- Microsoft GUIDE SOC triage dataset.
"""
