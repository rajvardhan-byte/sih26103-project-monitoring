// Standalone Simulation Helper for What-If Analysis
function calculateInterventionImpact(currentDays, baseDelayMonths, baseOverrunCr) {
    const minDelay = 1;
    const simulatedDelay = Math.max(minDelay, Math.round((currentDays / 45) * baseDelayMonths));
    const costSaved = Math.max(0, baseOverrunCr - Math.round((currentDays / 45) * baseOverrunCr));

    return {
        simulatedDelayMonths: simulatedDelay,
        costSavedCr: costSaved
    };
}