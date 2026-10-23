"""Generate wholly synthetic, illustrative inputs (no contest attachments)."""
import csv
import math
from pathlib import Path

path = Path(__file__).resolve().parent / "synthetic_day.csv"
with path.open("w", encoding="utf-8", newline="") as file:
    out=csv.writer(file)
    out.writerow(["start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh"])
    for k in range(144):
        hour=(k+.5)/6
        load_kw=2900+450*math.sin(2*math.pi*(hour-7)/24)+600*math.exp(-((hour-19)/2.5)**2)
        pv_kw=3200*max(0, math.sin(math.pi*(hour-6)/12))**2 if 6<=hour<=18 else 0
        price=0.35 if hour<7 else 0.70 if hour<17 else 1.20 if hour<22 else 0.45
        out.writerow([10*k,10*(k+1),f"{load_kw/6:.6f}",f"{pv_kw/6:.6f}",f"{price:.4f}"])
print(f"Created {path} using synthetic input values")
