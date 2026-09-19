# ECO DEFENDERS — Data Resources & Dataset Documentation

## Overview

ECO DEFENDERS uses high-frequency hydrological and meteorological time-series telemetry collected from distributed IoT sensor nodes deployed in disaster-prone river basins and dam catchments.

---

## Sourced & Benchmark Datasets

### 1. USGS Water Data for the Nation
- **Source**: United States Geological Survey (USGS) NWIS
- **URL**: [https://waterdata.usgs.gov/nwis](https://waterdata.usgs.gov/nwis)
- **Variables**: Stream stage (gage height in meters), river discharge ($m^3/s$), precipitation accumulation ($mm$).
- **Relevance**: Serves as the hydrological ground-truth baseline for river stage hydrograph dynamics and stage-discharge rating curves.

### 2. NOAA National Weather Service Precipitation Telemetry
- **Source**: NOAA National Centers for Environmental Information (NCEI)
- **URL**: [https://www.ncdc.noaa.gov/](https://www.ncdc.noaa.gov/)
- **Variables**: Rainfall intensity ($mm/hr$), atmospheric pressure ($hPa$), ambient temperature ($^\circ C$), relative humidity ($\%$), wind speed ($m/s$).
- **Relevance**: Provides storm event precipitation rates and pressure drop indicators preceding monsoon deluges.

### 3. Kaggle Hydrological Multivariate FlowDB Dataset
- **Source**: FlowDB Open Hydrology Benchmark
- **URL**: [https://www.kaggle.com/datasets/paultimothymooney/flowdb-sample](https://www.kaggle.com/datasets/paultimothymooney/flowdb-sample)
- **Variables**: Multi-sensor gauge height, precipitation, flash flood event labels, temperature.
- **Relevance**: Provenance-validated multivariate hydrological dataset used for benchmark comparison.

---

## Data Preprocessing & Pipeline Architecture

Raw sensor data undergoes standardized transformation in `src/data_pipeline.py`:

1. **Unit Standardization**:
   - Rainfall: millimeters ($mm$)
   - Water Level: meters ($m$) above gauge zero
   - River Flow: cubic meters per second ($m^3/s$)
   - Soil Moisture: percentage ($\%$)
   - Pressure: hectopascals ($hPa$)
2. **Quality Control & Outlier Filtering**:
   - Rejects negative rainfall or water levels.
   - Caps soil moisture to $[0\%, 100\%]$.
3. **Temporal Feature Engineering (Zero Target Leakage)**:
   - Rolling Rain Accumulations: 15m, 30m, 1h, 3h, 6h.
   - Water Level Rate of Rise ($dL/dt$ in $m/hr$).
   - Water Level 3-hour Maximum ($m$) and 1-hour Mean ($m$).
   - Dam Fill Ratio: $\frac{\text{Dam Water Level}}{\text{Dam Capacity}}$.
4. **Target Formulation**:
   - Future 60-minute prediction horizon ($T_{horizon} = 60\text{ min}$).
   - Target = $1$ if future water level breaches danger threshold stage $L_{danger}$, else $0$.
   - Chronological split: 70% Train, 15% Validation, 15% Test.
