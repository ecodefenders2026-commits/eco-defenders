# MODEL CARD — XGBoost Flood Prediction Engine v1.0.0

## Model Details
- **Model Name**: XGBoost Flood Risk Classifier (`xgboost_flood_v1.json`)
- **Developer**: ECO DEFENDERS ML Engineering Team
- **Version**: 1.0.0
- **Model Architecture**: Gradient Boosted Decision Trees (`xgb.XGBClassifier`)
- **Serialization Format**: Native XGBoost JSON schema + Joblib StandardScaler

---

## Intended Use
- **Primary Purpose**: Early warning flood risk assessment for river basins, dam catchments, and vulnerable coastal areas.
- **Horizon**: 60-minute future prediction horizon given current and recent 60-minute IoT sensor observations.
- **Intended Users**: Emergency management officials, municipal disaster response teams, and public safety dashboard operators.

---

## Non-Intended Use & Operational Limitations
- **Certified Emergency Warning System Notice**: This prototype model is intended for decision-support and prototype demonstration. It must not be deployed as an unmonitored automated life-safety shutoff or evacuation trigger without field validation and multi-sensor hardware redundancy.
- **Geographic Limits**: Trained on river basin gauge profiles with danger thresholds between $4.8m$ and $6.2m$. Re-calibration is required for new river topographies.
- **Sensor Failure Dependency**: Relies on accurate water level and rainfall readings; sensor failures are flagged by the validator layer.

---

## Training Data & Hyperparameters
- **Dataset Split**: Chronological Time-Series Split (70% Train, 15% Validation, 15% Test — No random row shuffling).
- **Train Rows**: 30,239 | **Test Rows**: 6,480
- **Hyperparameters**:
  - `n_estimators`: 200
  - `max_depth`: 6
  - `learning_rate`: 0.05
  - `subsample`: 0.8
  - `colsample_bytree`: 0.8
  - `min_child_weight`: 3
  - `gamma`: 0.1
  - `scale_pos_weight`: 2.70

---

## Model Evaluation Metrics

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **XGBoost (Primary)** | **0.9963** | **0.9977** | **0.9886** | **0.9932** | **0.9999** |
| Random Forest | 0.9974 | 0.9966 | 0.9938 | 0.9952 | 0.9999 |
| Decision Tree | 0.9941 | 0.9960 | 0.9824 | 0.9891 | 0.9882 |
| Logistic Regression | 0.9960 | 0.9926 | 0.9926 | 0.9926 | 0.9999 |

### Tradeoff Analysis
For a disaster warning system, **false negatives** (missed flood events) are significantly more dangerous than false positives (false alarms). XGBoost achieved a recall of 98.86% and precision of 99.77% with an inference latency under 5 milliseconds per request.
