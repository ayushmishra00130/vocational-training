const API_BASE = "/api/v1";
const STORAGE_KEY = "latest-assessment";

function byId(id) {
    return document.getElementById(id);
}

function show(element) {
    if (element) {
        element.classList.remove("hidden");
    }
}

function hide(element) {
    if (element) {
        element.classList.add("hidden");
    }
}

function setText(id, text) {
    const node = byId(id);
    if (node) {
        node.textContent = text;
    }
}

function parseJsonScript(scriptId) {
    const node = byId(scriptId);
    if (!node || !node.textContent) {
        return null;
    }

    try {
        return JSON.parse(node.textContent);
    } catch (error) {
        return null;
    }
}

function createDebounce(callback, delayMs) {
    let timer = null;
    return (...args) => {
        if (timer) {
            window.clearTimeout(timer);
        }
        timer = window.setTimeout(() => callback(...args), delayMs);
    };
}

function saveAssessmentBundle(bundle) {
    try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(bundle));
    } catch (error) {
        // Storage can fail in restrictive browsing modes; continue without persisting.
    }
}

function loadStoredAssessmentBundle() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return null;
        }
        return JSON.parse(raw);
    } catch (error) {
        return null;
    }
}

function smokingToSliderValue(smoking) {
    if (smoking === "current") {
        return 2;
    }
    if (smoking === "former") {
        return 1;
    }
    return 0;
}

function sliderValueToSmoking(value) {
    if (Number(value) >= 2) {
        return "current";
    }
    if (Number(value) === 1) {
        return "former";
    }
    return "never";
}

function smokingLabel(smoking) {
    if (smoking === "current") {
        return "Current";
    }
    if (smoking === "former") {
        return "Former";
    }
    return "Never";
}

function renderRiskBadge(risk) {
    const badge = byId("risk-badge");
    if (!badge) {
        return;
    }

    badge.textContent = risk || "-";
    badge.classList.remove("low", "medium", "high");
    if (risk) {
        badge.classList.add(String(risk).toLowerCase());
    }
}

function renderRecommendations(items) {
    const list = byId("recommendation-list");
    if (!list) {
        return;
    }

    list.innerHTML = "";
    (items || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
    });
}

function driverStatusForImpact(impactPercent) {
    const value = Number(impactPercent) || 0;
    if (value >= 40) {
        return { label: "High", className: "high" };
    }
    if (value >= 22) {
        return { label: "Moderate", className: "moderate" };
    }
    return { label: "Low", className: "low" };
}

function renderDriverStatuses(drivers) {
    const list = byId("driver-status-list");
    if (!list) {
        return;
    }

    list.innerHTML = "";
    (drivers || []).forEach((driver) => {
        const row = document.createElement("li");
        row.className = "driver-status-item";

        const name = document.createElement("strong");
        name.textContent = driver.label || "Driver";

        const status = driverStatusForImpact(driver.impact_percent);
        const pill = document.createElement("span");
        pill.className = `driver-pill ${status.className}`;
        pill.textContent = status.label;

        row.appendChild(name);
        row.appendChild(pill);
        list.appendChild(row);
    });
}

function hexToRgb(hex) {
    const value = hex.replace("#", "");
    const normalized = value.length === 3
        ? value.split("").map((ch) => ch + ch).join("")
        : value;

    const intValue = Number.parseInt(normalized, 16);
    return {
        r: (intValue >> 16) & 255,
        g: (intValue >> 8) & 255,
        b: intValue & 255,
    };
}

function rgbToHex(r, g, b) {
    const channel = (value) => Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, "0");
    return `#${channel(r)}${channel(g)}${channel(b)}`;
}

function interpolateHexColor(startHex, endHex, ratio) {
    const t = Math.max(0, Math.min(1, Number(ratio) || 0));
    const start = hexToRgb(startHex);
    const end = hexToRgb(endHex);
    return rgbToHex(
        start.r + (end.r - start.r) * t,
        start.g + (end.g - start.g) * t,
        start.b + (end.b - start.b) * t
    );
}

function setSimulationAccent(probability) {
    const accent = interpolateHexColor("#2f6a9b", "#d2833c", probability);
    document.documentElement.style.setProperty("--sim-accent", accent);
}

function gaugeColorForProbability(probability) {
    if (probability < 0.35) {
        return "#2f8d62";
    }
    if (probability < 0.7) {
        return "#b68435";
    }
    return "#b13a34";
}

function registerGaugePlugin() {
    if (!window.Chart || window.__riskGaugePluginRegistered) {
        return;
    }

    const gaugeTextPlugin = {
        id: "gaugeTextPlugin",
        afterDraw(chart) {
            const dataset = chart?.data?.datasets?.[0];
            if (!dataset || !dataset.data || typeof dataset.data[0] !== "number") {
                return;
            }

            const value = dataset.data[0];
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;
            const x = chartArea ? (chartArea.left + chartArea.right) / 2 : chart.getDatasetMeta(0)?.data?.[0]?.x;
            const y = chartArea ? chartArea.bottom - 26 : chart.getDatasetMeta(0)?.data?.[0]?.y;
            if (!x || !y) {
                return;
            }

            const width = chart.width || 320;
            const valueSize = Math.max(20, Math.min(34, Math.round(width / 11)));
            const labelSize = Math.max(10, Math.min(13, Math.round(width / 28)));

            ctx.save();
            ctx.textAlign = "center";
            ctx.fillStyle = "#103252";
            ctx.font = `800 ${valueSize}px Plus Jakarta Sans`;
            ctx.fillText(`${value.toFixed(1)}%`, x, y);
            ctx.font = `700 ${labelSize}px Plus Jakarta Sans`;
            ctx.fillStyle = "#4a6681";
            ctx.fillText("Estimated Risk", x, y + labelSize + 7);
            ctx.restore();
        },
    };

    Chart.register(gaugeTextPlugin);
    window.__riskGaugePluginRegistered = true;
}

function createGaugeChart(context, probability) {
    registerGaugePlugin();
    const riskPercent = Math.max(1, Math.min(99, Number(probability) * 100));

    return new Chart(context, {
        type: "doughnut",
        data: {
            datasets: [
                {
                    data: [riskPercent, 100 - riskPercent],
                    backgroundColor: [gaugeColorForProbability(Number(probability)), "#deebf6"],
                    borderWidth: 0,
                    cutout: "70%",
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 120,
            rotation: -90,
            circumference: 180,
            layout: {
                padding: {
                    top: 8,
                    left: 8,
                    right: 8,
                    bottom: 18,
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
    });
}

function createDriversChart(context, drivers) {
    const labels = (drivers || []).map((driver) => driver.label);
    const values = (drivers || []).map((driver) => driver.impact_percent);

    return new Chart(context, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: ["#2f6a9b", "#4a83b2", "#7ba7cb"],
                    borderRadius: 8,
                },
            ],
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 120,
            layout: {
                padding: {
                    top: 8,
                    left: 4,
                    right: 8,
                    bottom: 4,
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.parsed.x}% contribution`,
                    },
                },
            },
            scales: {
                x: {
                    min: 0,
                    max: 100,
                    ticks: {
                        color: "#2a4d6e",
                        font: { weight: "600" },
                        callback: (value) => `${value}%`,
                    },
                    grid: { color: "rgba(31, 79, 121, 0.12)" },
                },
                y: {
                    ticks: {
                        color: "#163a5d",
                        font: { weight: "700" },
                    },
                    grid: { display: false },
                },
            },
        },
    });
}

function updateGaugeChart(chart, probability) {
    if (!chart) {
        return;
    }

    const riskPercent = Math.max(1, Math.min(99, Number(probability) * 100));
    chart.data.datasets[0].data = [riskPercent, 100 - riskPercent];
    chart.data.datasets[0].backgroundColor = [gaugeColorForProbability(Number(probability)), "#deebf6"];
    chart.update();
}

function updateDriversChart(chart, drivers) {
    if (!chart) {
        return;
    }

    chart.data.labels = (drivers || []).map((driver) => driver.label);
    chart.data.datasets[0].data = (drivers || []).map((driver) => driver.impact_percent);
    chart.update();
}

function chooseLatestBundle(serverBundle, storageBundle) {
    if (serverBundle && serverBundle.payload && serverBundle.prediction) {
        if (!storageBundle || !storageBundle.payload || !storageBundle.prediction) {
            return serverBundle;
        }

        const serverTime = Date.parse(serverBundle.prediction.assessed_at || "") || 0;
        const storageTime = Date.parse(storageBundle.prediction.assessed_at || "") || 0;
        return serverTime >= storageTime ? serverBundle : storageBundle;
    }

    return storageBundle;
}

function collectAssessmentPayload() {
    return {
        age: Number(byId("age").value),
        sex: byId("sex").value,
        blood_pressure: Number(byId("blood_pressure").value),
        cholesterol: Number(byId("cholesterol").value),
        chest_pain: byId("chest_pain").value,
        shortness_of_breath: byId("shortness_of_breath").checked,
        fatigue: byId("fatigue").checked,
        irregular_heartbeat: byId("irregular_heartbeat").checked,
        smoking: byId("smoking").value,
        diabetes: byId("diabetes").checked,
    };
}

function validateStepOne() {
    const age = Number(byId("age").value);
    const bp = Number(byId("blood_pressure").value);
    const cholesterol = Number(byId("cholesterol").value);

    if (!Number.isFinite(age) || !Number.isFinite(bp) || !Number.isFinite(cholesterol)) {
        return "Please enter age, blood pressure, and cholesterol values.";
    }

    if (age < 18 || age > 120) {
        return "Biological Outlier: Age appears outside realistic human screening bounds (18-120).";
    }

    if (bp < 70 || bp > 260) {
        return "Biological Outlier: Blood Pressure appears outside realistic clinical bounds (70-260 mmHg).";
    }

    if (cholesterol < 80 || cholesterol > 700) {
        return "Biological Outlier: Cholesterol appears outside realistic lab bounds (80-700 mg/dL).";
    }

    return null;
}

function initAssessmentPage() {
    const form = byId("assessment-form");
    if (!form) {
        return;
    }

    const steps = Array.from(document.querySelectorAll(".form-step"));
    const btnPrev = byId("btn-prev");
    const btnNext = byId("btn-next");
    const btnSubmit = byId("btn-submit");
    const progressLabel = byId("progress-label");
    const progressPercent = byId("progress-percent");
    const progressFill = byId("progress-fill");
    const errorBox = byId("wizard-error");
    const totalSteps = steps.length;

    let currentStep = 1;

    function showError(message) {
        if (!errorBox) {
            return;
        }
        errorBox.textContent = message;
        show(errorBox);
    }

    function clearError() {
        if (!errorBox) {
            return;
        }
        errorBox.textContent = "";
        hide(errorBox);
    }

    function updateProgress() {
        const percent = Math.round((currentStep / totalSteps) * 100);
        steps.forEach((step, index) => {
            if (index + 1 === currentStep) {
                show(step);
            } else {
                hide(step);
            }
        });

        progressLabel.textContent = `Step ${currentStep} of ${totalSteps}`;
        progressPercent.textContent = `${percent}%`;
        progressFill.style.width = `${percent}%`;

        btnPrev.disabled = currentStep === 1;

        if (currentStep === totalSteps) {
            hide(btnNext);
            show(btnSubmit);
        } else {
            show(btnNext);
            hide(btnSubmit);
        }
    }

    function validateCurrentStep() {
        clearError();

        if (currentStep === 1) {
            const stepOneError = validateStepOne();
            if (stepOneError) {
                showError(stepOneError);
                return false;
            }
        }

        return true;
    }

    btnNext.addEventListener("click", () => {
        if (!validateCurrentStep()) {
            return;
        }
        currentStep = Math.min(totalSteps, currentStep + 1);
        updateProgress();
    });

    btnPrev.addEventListener("click", () => {
        clearError();
        currentStep = Math.max(1, currentStep - 1);
        updateProgress();
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!validateCurrentStep()) {
            return;
        }

        const payload = collectAssessmentPayload();
        btnSubmit.disabled = true;
        btnSubmit.textContent = "Generating Dashboard...";

        try {
            const response = await fetch(`${API_BASE}/predict`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Could not process assessment.");
            }

            saveAssessmentBundle({ payload, prediction: result });
            window.location.href = result.result_url || "/results";
        } catch (error) {
            showError(error.message || "Something went wrong. Please try again.");
        } finally {
            btnSubmit.disabled = false;
            btnSubmit.textContent = "Generate My Clinical Dashboard";
        }
    });

    updateProgress();
}

function initHomePage() {
    return;
}

function initResultsPage() {
    const dashboard = byId("results-dashboard");
    if (!dashboard) {
        return;
    }

    const emptyMessage = byId("results-empty");
    const serverBundle = parseJsonScript("latest-assessment-data");
    const storageBundle = loadStoredAssessmentBundle();
    const resultsMetadata = parseJsonScript("results-metadata") || {};
    const activeBundle = resultsMetadata.source === "historic"
        ? serverBundle
        : chooseLatestBundle(serverBundle, storageBundle);

    if (!activeBundle || !activeBundle.payload || !activeBundle.prediction) {
        hide(dashboard);
        show(emptyMessage);
        return;
    }

    hide(emptyMessage);
    show(dashboard);
    if (resultsMetadata.source !== "historic") {
        saveAssessmentBundle(activeBundle);
    }

    const state = {
        originalPayload: { ...activeBundle.payload },
        currentPayload: { ...activeBundle.payload },
        baselineRecommendations: Array.isArray(activeBundle.prediction.recommendations)
            ? [...activeBundle.prediction.recommendations]
            : [],
        gaugeChart: null,
        driversChart: null,
    };

    const gaugeCanvas = byId("risk-gauge-chart");
    const driversCanvas = byId("drivers-chart");

    if (window.Chart && gaugeCanvas) {
        state.gaugeChart = createGaugeChart(gaugeCanvas, activeBundle.prediction.risk_probability);
    }

    if (window.Chart && driversCanvas) {
        state.driversChart = createDriversChart(driversCanvas, activeBundle.prediction.primary_drivers || []);
    }

    window.setTimeout(() => {
        if (state.gaugeChart) {
            state.gaugeChart.resize();
        }
        if (state.driversChart) {
            state.driversChart.resize();
        }
    }, 80);

    function renderPrediction(prediction, mode) {
        renderRiskBadge(prediction.risk);
        setText("risk-probability", `${(Number(prediction.risk_probability) * 100).toFixed(1)}%`);
        setText("heart-age", `${prediction.heart_age} yrs`);
        setText("risk-summary", prediction.risk_summary || "");
        renderDriverStatuses(prediction.primary_drivers || []);
        setSimulationAccent(prediction.risk_probability);

        // Keep recommendations tied to original assessment input, not simulation tweaks.
        if (mode === "simulation") {
            renderRecommendations(state.baselineRecommendations);
        } else {
            const baseline = Array.isArray(prediction.recommendations) ? prediction.recommendations : [];
            state.baselineRecommendations = [...baseline];
            renderRecommendations(state.baselineRecommendations);
        }

        const penalties = prediction.heart_age_penalties || {};
        setText(
            "heart-age-breakdown",
            `Heart Age penalties -> Smoking: +${penalties.Smoking || 0}, High BP: +${penalties["High BP"] || 0}, Diabetes: +${penalties.Diabetes || 0}`
        );

        updateGaugeChart(state.gaugeChart, prediction.risk_probability);
        updateDriversChart(state.driversChart, prediction.primary_drivers || []);

        if (mode === "simulation") {
            setText("results-subtitle", "Simulation mode: risk is recalculated live as you change modifiable factors.");
        } else {
            setText(
                "results-subtitle",
                "Interactive risk analysis, explainability, simulation, and printable medical summary."
            );
        }
    }

    renderPrediction(activeBundle.prediction, "baseline");

    const simBp = byId("sim-bp");
    const simChol = byId("sim-chol");
    const simSmoking = byId("sim-smoking");
    const simDiabetes = byId("sim-diabetes");
    const simDiabetesToggle = byId("sim-diabetes-toggle");
    const simDiabetesText = byId("sim-diabetes-text");

    function syncSliderLabels() {
        setText("sim-bp-value", `${simBp.value} mmHg`);
        setText("sim-chol-value", `${simChol.value} mg/dL`);
        setText("sim-smoking-value", smokingLabel(sliderValueToSmoking(simSmoking.value)));
        setText("sim-diabetes-value", simDiabetes.checked ? "Yes" : "No");

        if (simDiabetesToggle) {
            simDiabetesToggle.classList.toggle("is-on", simDiabetes.checked);
            simDiabetesToggle.setAttribute("aria-pressed", simDiabetes.checked ? "true" : "false");
        }
        if (simDiabetesText) {
            simDiabetesText.textContent = simDiabetes.checked ? "Modifier On" : "Modifier Off";
        }
    }

    function sliderPayload() {
        return {
            ...state.originalPayload,
            blood_pressure: Number(simBp.value),
            cholesterol: Number(simChol.value),
            smoking: sliderValueToSmoking(simSmoking.value),
            diabetes: Boolean(simDiabetes.checked),
        };
    }

    async function runSimulation() {
        const payload = sliderPayload();
        state.currentPayload = payload;

        try {
            const response = await fetch(`${API_BASE}/predict?mode=simulation`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Simulation failed.");
            }

            renderPrediction(result, "simulation");
        } catch (error) {
            setText("results-subtitle", error.message || "Simulation request failed.");
        }
    }

    const debouncedSimulation = createDebounce(runSimulation, 220);

    if (simBp && simChol && simSmoking && simDiabetes) {
        simBp.value = Math.max(90, Math.min(200, Number(state.originalPayload.blood_pressure)));
        simChol.value = Math.max(120, Math.min(360, Number(state.originalPayload.cholesterol)));
        simSmoking.value = smokingToSliderValue(state.originalPayload.smoking);
        simDiabetes.checked = Boolean(state.originalPayload.diabetes);

        syncSliderLabels();

        [simBp, simChol, simSmoking].forEach((slider) => {
            slider.addEventListener("input", () => {
                syncSliderLabels();
                debouncedSimulation();
            });
        });

        simDiabetes.addEventListener("change", () => {
            syncSliderLabels();
            debouncedSimulation();
        });

        if (simDiabetesToggle) {
            simDiabetesToggle.addEventListener("click", () => {
                simDiabetes.checked = !simDiabetes.checked;
                syncSliderLabels();
                debouncedSimulation();
            });
        }
    }

    const resetBtn = byId("sim-reset");
    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            simBp.value = Math.max(90, Math.min(200, Number(state.originalPayload.blood_pressure)));
            simChol.value = Math.max(120, Math.min(360, Number(state.originalPayload.cholesterol)));
            simSmoking.value = smokingToSliderValue(state.originalPayload.smoking);
            simDiabetes.checked = Boolean(state.originalPayload.diabetes);
            syncSliderLabels();
            runSimulation();
        });
    }

    const downloadBtn = byId("download-report");
    if (downloadBtn) {
        downloadBtn.addEventListener("click", async () => {
            downloadBtn.disabled = true;
            downloadBtn.textContent = "Preparing PDF...";

            try {
                const response = await fetch(`${API_BASE}/report`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ payload: state.originalPayload }),
                });

                if (!response.ok) {
                    const failure = await response.json();
                    throw new Error(failure.error || "PDF generation failed.");
                }

                const blob = await response.blob();
                const fileUrl = URL.createObjectURL(blob);
                const anchor = document.createElement("a");
                anchor.href = fileUrl;
                anchor.download = "Medical_Summary.pdf";
                document.body.appendChild(anchor);
                anchor.click();
                anchor.remove();
                URL.revokeObjectURL(fileUrl);
            } catch (error) {
                setText("results-subtitle", error.message || "Could not download report.");
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.textContent = "Download Medical Summary";
            }
        });
    }
}

function initPage() {
    const page = document.body.getAttribute("data-page");

    if (page === "home") {
        initHomePage();
    }

    if (page === "assess") {
        initAssessmentPage();
    }

    if (page === "results") {
        initResultsPage();
    }
}

document.addEventListener("DOMContentLoaded", initPage);