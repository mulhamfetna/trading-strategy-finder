from optimize.l2 import payload as P

print("champion sets the dashboard can serve:")
for s in P.available_champion_sets():
    print(f"    {s['name']:9} | {s['label']:42} | verified: {s['verified']}")
print()
print(f"{'slot':8} | {'DEPLOYED (holds overnight)':<34} | {'eod1 (forced end-of-day)':<34}")
print("-" * 84)
for inst, tf in (("NQ", "4h"), ("GC", "15m"), ("YM", "4h"), ("CL", "2h"), ("RTY", "1h")):
    a = P.instrument_l1_default(inst, tf, "deployed")
    b = P.instrument_l1_default(inst, tf, "eod1")
    fa = f"cap={a.get('cap_mode')}/{a.get('cap_1min')}  ind_1min={a.get('ind_1min')}"
    fb = f"cap={b.get('cap_mode')}/{b.get('cap_1min')}  ind_1min={b.get('ind_1min')}"
    print(f"{inst + ' ' + tf:8} | {fa:<34} | {fb:<34}")
