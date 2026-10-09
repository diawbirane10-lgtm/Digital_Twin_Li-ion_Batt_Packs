"""Brand-independent CSV analysis. No OEM health certificate is inferred."""
import csv
import hashlib
import io
import math
import statistics

REQUIRED = ('time_s', 'pack_voltage_v', 'pack_current_a')
OPTIONAL = ('temperature_c', 'soc_pct', 'cell_min_v', 'cell_max_v')

def positive_area(a, b, hours):
    """Integral of positive part of a linearly interpolated signal."""
    if a >= 0 and b >= 0: return (a+b)*hours/2
    if a <= 0 and b <= 0: return 0.0
    if a > 0: return hours*a*a/(2*(a-b))
    return hours*b*b/(2*(b-a))

def analyse_csv(text: str, current_convention: str, thresholds: dict, metadata: dict):
    if len(text.encode('utf-8')) > 5_000_000:
        raise ValueError('Fichier limité à 5 Mo.')
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    headers = reader.fieldnames or []
    if not all(k in headers for k in REQUIRED):
        raise ValueError('Colonnes requises : ' + ', '.join(REQUIRED))
    if len(headers) != len(set(headers)): raise ValueError('En-têtes dupliqués : colonnes ambiguës.')
    rows = []
    for index, raw in enumerate(reader, 2):
        if index > 20001: raise ValueError('Maximum 20 000 lignes.')
        row = {}
        for key in REQUIRED + OPTIONAL:
            if key not in headers: continue
            try: value = float(raw[key])
            except (ValueError, TypeError): raise ValueError(f'Ligne {index} : valeur invalide pour {key}.')
            if not math.isfinite(value): raise ValueError(f'Ligne {index} : valeur non finie pour {key}.')
            row[key] = value
        if row['pack_voltage_v'] <= 0: raise ValueError(f'Ligne {index} : tension pack non positive.')
        if 'soc_pct' in row and not 0 <= row['soc_pct'] <= 100: raise ValueError(f'Ligne {index} : SOC hors [0,100].')
        if ('cell_min_v' in row) != ('cell_max_v' in row): raise ValueError('Fournissez ensemble cell_min_v et cell_max_v.')
        if 'cell_min_v' in row and (row['cell_min_v'] <= 0 or row['cell_max_v'] < row['cell_min_v']):
            raise ValueError(f'Ligne {index} : tensions cellule incohérentes.')
        if rows and row['time_s'] <= rows[-1]['time_s']: raise ValueError(f'Ligne {index} : temps non strictement croissant.')
        row['current_discharge_a'] = row['pack_current_a'] * (1 if current_convention == 'positive_discharge' else -1)
        rows.append(row)
    if len(rows) < 2: raise ValueError('Au moins deux mesures sont nécessaires.')
    intervals = [b['time_s']-a['time_s'] for a,b in zip(rows,rows[1:])]
    dt = statistics.median(intervals)
    gaps = sum(v > 5*dt for v in intervals)
    discharge_wh = charge_wh = discharge_ah = charge_ah = 0.0
    for a,b in zip(rows,rows[1:]):
        duration=(b['time_s']-a['time_s'])/3600
        # Split sign crossings under a piecewise-linear interpolation.
        currents=[a['current_discharge_a'],b['current_discharge_a']]
        powers=[a['pack_voltage_v']*currents[0],b['pack_voltage_v']*currents[1]]
        discharge_ah += positive_area(*currents,duration)
        charge_ah += positive_area(-currents[0],-currents[1],duration)
        discharge_wh += positive_area(*powers,duration)
        charge_wh += positive_area(-powers[0],-powers[1],duration)
    findings = []
    def finding(code, severity, title, evidence, limitation):
        findings.append(dict(code=code,severity=severity,title=title,evidence=evidence,limitation=limitation))
    if gaps: finding('sampling_gaps','warning','Lacunes dans l’échantillonnage',f'{gaps} intervalles supérieurs à 5 × le pas médian ({dt:.3f} s).','Les intégrales interpolent entre mesures : précision non garantie dans ces intervalles.')
    temp = max((r['temperature_c'] for r in rows), default=None) if 'temperature_c' in headers else None
    if temp is not None and temp > thresholds['temperature_c']:
        finding('temperature','warning','Température au-dessus du seuil d’analyse',f'{temp:.2f} °C > {thresholds["temperature_c"]:.2f} °C.','Seuil choisi par l’analyste, pas une limite constructeur. La position du capteur est à documenter.')
    spread = max((r['cell_max_v']-r['cell_min_v'] for r in rows),default=None) if 'cell_min_v' in headers else None
    if spread is not None and spread > thresholds['cell_spread_v'] + 1e-9:
        finding('cell_spread','warning','Dispersion des tensions cellule',f'Écart maximal {spread*1000:.1f} mV > {thresholds["cell_spread_v"]*1000:.1f} mV.','Une dispersion sous charge ne prouve pas une cellule défectueuse; comparer courant, SOC et repos.')
    if not findings: finding('no_threshold_crossing','info','Aucun dépassement détecté dans les signaux disponibles','Analyse descriptive du fichier importé.','Cela ne certifie pas l’absence de défaut; couverture et seuils limités.')
    capabilities = dict(temperature='available' if temp is not None else 'missing_sensor',cell_spread='available' if spread is not None else 'missing_cell_voltages',soh='insufficient_evidence',rul='insufficient_evidence',weak_cell_localisation='insufficient_evidence')
    series=rows[::max(1,math.ceil(len(rows)/600))]
    if series[-1] is not rows[-1]: series.append(rows[-1])
    return dict(schema_version='1.0',sha256=hashlib.sha256(text.encode()).hexdigest(),metadata=metadata,
        current_convention=current_convention,thresholds=thresholds,metrics=dict(samples=len(rows),duration_s=rows[-1]['time_s']-rows[0]['time_s'],median_step_s=dt,sampling_gaps=gaps,discharge_wh=discharge_wh,charge_wh=charge_wh,discharge_ah=discharge_ah,charge_ah=charge_ah,max_temperature_c=temp,max_cell_spread_v=spread),
        findings=findings,capabilities=capabilities,series=series,
        notes=['Charge et énergie intégrées sur la fenêtre, pas capacité totale ni SOH.','Courant positif interne = décharge. Intégration linéaire par morceaux avec séparation des changements de signe; approximation entre mesures.','Aucune connexion OBD/CAN ni commande envoyée au véhicule.','Résultats exploratoires, sans qualification constructeur.'])
