"""Performance harnesses for issue #54 (indicator cold-miss acceleration).

Contains only measurement + PoC code. Nothing here is imported by the production optimizer path, and
every accelerator ships behind a default-OFF flag so results stay bit-identical (speed only)."""
