"""Explicit adapter for repository NASA laboratory cell data (not vehicle packs)."""
import pandas as pd


def cycle_csv(frame):
    if len(frame) < 2 or frame['cell'].nunique() != 1 or frame['cycle_idx'].nunique() != 1:
        raise ValueError('Select exactly one cell and cycle with at least two measurements.')
    columns = {'time_s':'time_s','voltage_V':'pack_voltage_v','current_A':'pack_current_a','temp_C':'temperature_c'}
    # 1S1P laboratory cell: voltage is not scaled into a fictional EV pack.
    return frame[list(columns)].rename(columns=columns).to_csv(index=False)
