/* ============================================================
   ECO DEFENDERS
   Minimal AI Early Warning Interface
============================================================ */

const AppState = {

    hazard:
        "FLOOD",

    floodNode:
        "NODE_FLOOD_01",

    fireNode:
        "NODE_FIRE_01"
};


/* ============================================================
   START
============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        selectHazard(
            "FLOOD"
        );

    }
);


/* ============================================================
   HAZARD SELECTION
============================================================ */

function selectHazard(
    hazard
) {

    AppState.hazard =
        hazard;


    document
        .querySelectorAll(
            ".hazard-option"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.hazard === hazard
            );

        });


    const floodForm =
        document.getElementById(
            "flood-form"
        );

    const fireForm =
        document.getElementById(
            "fire-form"
        );

    const inputTitle =
        document.getElementById(
            "input-title"
        );

    const nodeLabel =
        document.getElementById(
            "node-label"
        );


    if (hazard === "FLOOD") {

        floodForm.classList.remove(
            "hidden"
        );

        fireForm.classList.add(
            "hidden"
        );

        inputTitle.textContent =
            "Flood Conditions";

        nodeLabel.textContent =
            AppState.floodNode;

        document.body.classList.remove(
            "fire-mode"
        );

    } else {

        floodForm.classList.add(
            "hidden"
        );

        fireForm.classList.remove(
            "hidden"
        );

        inputTitle.textContent =
            "Forest Fire Conditions";

        nodeLabel.textContent =
            AppState.fireNode;

        document.body.classList.add(
            "fire-mode"
        );
    }


    /*
     * Reset result when user switches hazard.
     */
    resetResult();
}


/* ============================================================
   FLOOD ANALYSIS
============================================================ */

async function runFloodAnalysis(
    event
) {

    event.preventDefault();


    const button =
        document.getElementById(
            "flood-submit"
        );


    setButtonLoading(
        button,
        true,
        "ANALYSING FLOOD RISK..."
    );


    const payload = {

        node_id:
            AppState.floodNode,

        timestamp:
            new Date().toISOString(),

        water_level_m:
            number(
                "water",
                4.85
            ),

        rainfall_mm:
            number(
                "rainfall",
                38.5
            ),

        river_flow:
            number(
                "flow",
                190
            ),

        soil_moisture:
            number(
                "soil",
                78
            ),

        dam_water_level_m:
            number(
                "dam",
                22.5
            ),

        dam_capacity:
            25.0,

        /*
         * Existing backend expects these
         * contextual values as well.
         */
        temperature:
            25.0,

        humidity:
            80.0,

        pressure:
            1002.0,

        wind_speed:
            14.2,

        latitude:
            18.1234,

        longitude:
            78.5678
    };


    try {

        const response =
            await fetch(
                "/api/v1/predict/flood",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(payload)
                }
            );


        if (!response.ok) {

            throw new Error(
                await getApiError(
                    response
                )
            );
        }


        const data =
            await response.json();


        showResult(
            data,
            "FLOOD",
            payload
        );

    } catch (error) {

        showError(
            error.message
        );

    } finally {

        setButtonLoading(
            button,
            false,
            "RUN AI ANALYSIS"
        );
    }
}


/* ============================================================
   FIRE ANALYSIS
============================================================ */

async function runFireAnalysis(
    event
) {

    event.preventDefault();


    const button =
        document.getElementById(
            "fire-submit"
        );


    setButtonLoading(
        button,
        true,
        "ANALYSING FIRE RISK..."
    );


    const payload = {

        node_id:
            AppState.fireNode,

        timestamp:
            new Date().toISOString(),

        thermal_temp_c:
            number(
                "thermal",
                88.5
            ),

        pm25_ugm3:
            number(
                "pm25",
                220
            ),

        ambient_temp_c:
            number(
                "ambient",
                38
            ),

        humidity_pct:
            number(
                "humidity",
                18
            ),

        wind_speed_ms:
            number(
                "wind",
                15.5
            ),

        co2_ppm:
            520.0,

        fuel_moisture_pct:
            12.0,

        latitude:
            18.2500,

        longitude:
            78.6500
    };


    try {

        const response =
            await fetch(
                "/api/v1/predict/fire",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(payload)
                }
            );


        if (!response.ok) {

            throw new Error(
                await getApiError(
                    response
                )
            );
        }


        const data =
            await response.json();


        showResult(
            data,
            "FOREST_FIRE",
            payload
        );

    } catch (error) {

        showError(
            error.message
        );

    } finally {

        setButtonLoading(
            button,
            false,
            "RUN AI ANALYSIS"
        );
    }
}


/* ============================================================
   SHOW RESULT
============================================================ */

function showResult(
    data,
    hazard,
    input
) {

    const prediction =
        data?.prediction || data || {};


    const score =
        clamp(
            Number(
                prediction.risk_score ?? 0
            ),
            0,
            100
        );


    const category =
        normaliseRisk(
            prediction.risk_category,
            score
        );


    const probability =
        hazard === "FOREST_FIRE"

            ? Number(
                prediction.fire_probability
                ??
                score / 100
            )

            : Number(
                prediction.flood_probability
                ??
                score / 100
            );


    const confidence =
        prediction.confidence != null

            ? Number(
                prediction.confidence
            )

            : null;


    /*
     * Main score
     */

    const scoreElement =
        document.getElementById(
            "risk-score"
        );

    scoreElement.textContent =
        Math.round(score);

    scoreElement.style.color =
        riskColour(
            category
        );


    /*
     * Hazard title
     */

    document.getElementById(
        "result-hazard"
    ).textContent =
        hazard === "FOREST_FIRE"
            ? "FOREST FIRE RISK"
            : "FLOOD RISK";


    /*
     * Category
     */

    const state =
        document.getElementById(
            "risk-state"
        );

    state.textContent =
        category;

    state.className =
        "state-pill " +
        riskStateClass(
            category
        );


    /*
     * Warning
     */

    const warning =
        Boolean(
            prediction.warning_required
        )
        ||
        category === "HIGH"
        ||
        category === "CRITICAL";


    const warningBox =
        document.getElementById(
            "warning-box"
        );


    if (warning) {

        warningBox.classList.remove(
            "hidden"
        );


        document.getElementById(
            "warning-title"
        ).textContent =
            `${category} WARNING`;


        document.getElementById(
            "warning-text"
        ).textContent =
            buildWarningText(
                hazard,
                input,
                category
            );

    } else {

        warningBox.classList.add(
            "hidden"
        );
    }


    /*
     * Primary output
     */

    if (hazard === "FLOOD") {

        document.getElementById(
            "primary-output"
        ).textContent =
            `${input.water_level_m.toFixed(2)} m`;

    } else {

        document.getElementById(
            "primary-output"
        ).textContent =
            `${input.thermal_temp_c.toFixed(1)} °C`;
    }


    /*
     * Threshold status
     */

    const thresholdOutput =
        document.getElementById(
            "threshold-output"
        );


    if (hazard === "FLOOD") {

        thresholdOutput.textContent =
            input.water_level_m >= 5

                ? "BREACHED"

                : `${(
                    input.water_level_m / 5 * 100
                  ).toFixed(0)}% of limit`;

    } else {

        thresholdOutput.textContent =
            input.thermal_temp_c >= 65

                ? "BREACHED"

                : `${(
                    input.thermal_temp_c / 65 * 100
                  ).toFixed(0)}% of limit`;
    }


    /*
     * Warning horizon
     */

    const time =
        prediction.estimated_time_to_threshold_minutes;


    document.getElementById(
        "time-output"
    ).textContent =
        formatTime(
            time
        );


    /*
     * Confidence
     */

    document.getElementById(
        "confidence-output"
    ).textContent =
        confidence === null
            ? "—"
            : `${Math.round(
                confidence <= 1
                    ? confidence * 100
                    : confidence
              )}%`;


    /*
     * Interpretation
     */

    document.getElementById(
        "result-summary"
    ).textContent =
        buildSummary(
            hazard,
            category,
            input,
            probability
        );


    /*
     * Swap empty state -> result.
     */

    document.getElementById(
        "result-empty"
    ).classList.add(
        "hidden"
    );

    document.getElementById(
        "result-content"
    ).classList.remove(
        "hidden"
    );
}


/* ============================================================
   SUMMARY
============================================================ */

function buildSummary(
    hazard,
    category,
    input,
    probability
) {

    const probabilityText =
        `${Math.round(
            probability * 100
        )}%`;


    if (hazard === "FLOOD") {

        if (
            category === "CRITICAL"
            ||
            category === "HIGH"
        ) {

            return (
                `The AI identifies a ${category.toLowerCase()} ` +
                `flood risk with an estimated probability of ` +
                `${probabilityText}. ` +
                `River level, rainfall and catchment conditions ` +
                `indicate possible hazard escalation.`
            );
        }


        return (
            `Current hydrological conditions indicate ` +
            `${category.toLowerCase()} flood risk. ` +
            `The AI probability estimate is ${probabilityText}.`
        );
    }


    if (
        category === "CRITICAL"
        ||
        category === "HIGH"
    ) {

        return (
            `The AI identifies a ${category.toLowerCase()} ` +
            `wildfire risk with an estimated probability of ` +
            `${probabilityText}. ` +
            `Thermal and smoke indicators suggest elevated ` +
            `fire activity.`
        );
    }


    return (
        `Current thermal and atmospheric conditions indicate ` +
        `${category.toLowerCase()} wildfire risk. ` +
        `The AI probability estimate is ${probabilityText}.`
    );
}


/* ============================================================
   WARNING TEXT
============================================================ */

function buildWarningText(
    hazard,
    input,
    category
) {

    if (hazard === "FLOOD") {

        return (
            `River level is ${input.water_level_m.toFixed(2)} m ` +
            `against a 5.0 m danger stage. ` +
            `Immediate monitoring is recommended.`
        );
    }


    return (
        `Thermal hotspot is ${input.thermal_temp_c.toFixed(1)} °C ` +
        `with PM2.5 at ${input.pm25_ugm3.toFixed(0)} µg/m³. ` +
        `Wildfire conditions require attention.`
    );
}


/* ============================================================
   PRESETS — FLOOD
============================================================ */

function loadFloodPreset(
    preset
) {

    const values = {

        normal: {
            water: 1.8,
            rainfall: 0.5,
            flow: 25,
            soil: 38,
            dam: 12
        },

        moderate: {
            water: 3.4,
            rainfall: 20,
            flow: 90,
            soil: 65,
            dam: 16.5
        },

        critical: {
            water: 4.85,
            rainfall: 38.5,
            flow: 190,
            soil: 78,
            dam: 22.5
        }
    };


    const selected =
        values[preset];


    if (!selected) return;


    setValue(
        "water",
        selected.water
    );

    setValue(
        "rainfall",
        selected.rainfall
    );

    setValue(
        "flow",
        selected.flow
    );

    setValue(
        "soil",
        selected.soil
    );

    setValue(
        "dam",
        selected.dam
    );
}


/* ============================================================
   PRESETS — FIRE
============================================================ */

function loadFirePreset(
    preset
) {

    const values = {

        normal: {
            thermal: 26,
            pm25: 15,
            ambient: 26,
            humidity: 65,
            wind: 3
        },

        elevated: {
            thermal: 48,
            pm25: 70,
            ambient: 33,
            humidity: 28,
            wind: 9
        },

        wildfire: {
            thermal: 120,
            pm25: 360,
            ambient: 42,
            humidity: 12,
            wind: 22
        }
    };


    const selected =
        values[preset];


    if (!selected) return;


    setValue(
        "thermal",
        selected.thermal
    );

    setValue(
        "pm25",
        selected.pm25
    );

    setValue(
        "ambient",
        selected.ambient
    );

    setValue(
        "humidity",
        selected.humidity
    );

    setValue(
        "wind",
        selected.wind
    );
}


/* ============================================================
   RESULT RESET
============================================================ */

function resetResult() {

    document.getElementById(
        "result-empty"
    ).classList.remove(
        "hidden"
    );


    document.getElementById(
        "result-content"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "warning-box"
    ).classList.add(
        "hidden"
    );


    document.getElementById(
        "risk-score"
    ).textContent =
        "0";
}


/* ============================================================
   HELPERS
============================================================ */

function number(
    id,
    fallback
) {

    const element =
        document.getElementById(
            id
        );


    const value =
        parseFloat(
            element?.value
        );


    return Number.isFinite(value)
        ? value
        : fallback;
}


function setValue(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (element) {

        element.value =
            value;
    }
}


function clamp(
    value,
    min,
    max
) {

    return Math.max(
        min,
        Math.min(
            max,
            Number(value) || 0
        )
    );
}


function normaliseRisk(
    category,
    score
) {

    if (category) {

        const text =
            String(category)
                .trim()
                .toUpperCase();


        /*
         * Convert existing VERY LOW naming
         * into the shorter UI terminology.
         */
        if (
            text === "VERY LOW"
            ||
            text === "LOW"
        ) {
            return "LOW";
        }


        if (
            text === "MODERATE"
        ) {
            return "MODERATE";
        }


        if (
            text === "HIGH"
        ) {
            return "HIGH";
        }


        if (
            text === "CRITICAL"
        ) {
            return "CRITICAL";
        }
    }


    if (score <= 40) {
        return "LOW";
    }

    if (score <= 60) {
        return "MODERATE";
    }

    if (score <= 80) {
        return "HIGH";
    }

    return "CRITICAL";
}


function riskColour(
    category
) {

    switch (category) {

        case "LOW":
            return "#17865b";

        case "MODERATE":
            return "#b87800";

        case "HIGH":
            return "#c15b12";

        case "CRITICAL":
            return "#c93535";

        default:
            return "#102033";
    }
}


function riskStateClass(
    category
) {

    switch (category) {

        case "LOW":
            return "state-low";

        case "MODERATE":
            return "state-moderate";

        case "HIGH":
            return "state-high";

        case "CRITICAL":
            return "state-critical";

        default:
            return "state-low";
    }
}


function formatTime(
    minutes
) {

    if (
        minutes === null
        ||
        minutes === undefined
        ||
        !Number.isFinite(
            Number(minutes)
        )
    ) {
        return "—";
    }


    const value =
        Number(minutes);


    if (value <= 0) {
        return "NOW";
    }


    if (value < 60) {

        return `${Math.round(
            value
        )} min`;
    }


    const hours =
        Math.floor(
            value / 60
        );

    const mins =
        Math.round(
            value % 60
        );


    return `${hours}h ${mins}m`;
}


/* ============================================================
   BUTTON STATE
============================================================ */

function setButtonLoading(
    button,
    loading,
    text
) {

    if (!button) return;


    button.disabled =
        loading;


    const spans =
        button.querySelectorAll(
            "span"
        );


    if (spans.length > 0) {

        spans[0].textContent =
            text;
    }
}


/* ============================================================
   API ERROR
============================================================ */

async function getApiError(
    response
) {

    try {

        const data =
            await response.json();


        if (
            typeof data.detail ===
            "string"
        ) {
            return data.detail;
        }


        return JSON.stringify(
            data.detail || data
        );

    } catch {

        try {

            return await response.text();

        } catch {

            return `Server returned ${response.status}`;
        }
    }
}


/* ============================================================
   USER-FACING ERROR
============================================================ */

function showError(
    message
) {

    const empty =
        document.getElementById(
            "result-empty"
        );


    empty.classList.remove(
        "hidden"
    );


    document.getElementById(
        "result-content"
    ).classList.add(
        "hidden"
    );


    empty.querySelector(
        "h3"
    ).textContent =
        "Analysis failed";


    empty.querySelector(
        "p"
    ).textContent =
        message ||
        "Unable to connect to the AI inference service.";
}