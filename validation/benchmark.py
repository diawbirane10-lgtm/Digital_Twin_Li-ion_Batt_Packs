"""Reproducible measured-data integration benchmark; no SOC ground truth claimed."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from diagnostics.nasa import cycle_csv
from diagnostics.telemetry import analyse_csv

ROOT = Path(__file__).resolve().parents[1]

def run():
    path = ROOT/'data/processed/nasa_all_cycles.parquet'
    frame = pd.read_parquet(path)
    summary = pd.read_parquet(ROOT/'data/processed/nasa_summary.parquet')
    records = []
    for (cell, cycle), group in frame[frame.type == 'discharge'].groupby(['cell','cycle_idx']):
        result = analyse_csv(cycle_csv(group),'negative_discharge',{'temperature_c':55,'cell_spread_v':.1},{'source':'NASA repository processed data','data_kind':'measured','vehicle':'laboratory 1S1P'})
        t=group.time_s.to_numpy();i=-group.current_A.to_numpy()
        reference=float(np.trapezoid(np.maximum(i,0),t)/3600)
        label=summary[(summary.cell==cell)&(summary.cycle_idx==cycle)].capacity_Ah.iloc[0]
        records.append({'cell':cell,'cycle':int(cycle),'samples':len(group),'integrated_ah':result['metrics']['discharge_ah'],'reference_ah':reference,'nasa_capacity_label_ah':float(label),'label_difference_ah':result['metrics']['discharge_ah']-float(label),'sampling_gaps':result['metrics']['sampling_gaps']})
    differences=np.array([r['label_difference_ah'] for r in records])
    integration_errors=[abs(r['integrated_ah']-r['reference_ah']) for r in records]
    return {'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cells':sorted(frame.cell.unique().tolist()),'discharge_cycles':len(records),'samples':sum(r['samples'] for r in records),'max_numerical_reference_error_ah':max(integration_errors),'capacity_label_mae_ah':float(np.mean(abs(differences))),'capacity_label_max_error_ah':float(max(abs(differences))),'limitations':['Numerical reference uses the same current measurements, not independent sensor accuracy.','NASA capacity labels can use a different integration window/end-of-discharge criterion.','Laboratory cells do not validate an OEM vehicle diagnostic.','No independently measured SOC or fault labels in this benchmark.'],'per_cell':{cell:{'cycles':sum(r['cell']==cell for r in records),'capacity_label_mae_ah':float(np.mean([abs(r['label_difference_ah']) for r in records if r['cell']==cell]))} for cell in sorted(frame.cell.unique())}}

if __name__=='__main__':
    result=run();(ROOT/'validation/nasa_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cycles'},indent=2))
