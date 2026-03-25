function renderResults(results) {
  const summaryNode = document.getElementById("summary");
  const detailsNode = document.getElementById("details");
  const passedCount = results.filter((item) => item.passed).length;
  const failedResults = results.filter((item) => !item.passed);

  if (!summaryNode || !detailsNode) {
    throw new Error("Unit test runner DOM is not available.");
  }

  if (failedResults.length === 0) {
    summaryNode.dataset.status = "passed";
    summaryNode.textContent = `${passedCount} JS unit tests passed.`;
    detailsNode.textContent = "All tests passed.";
    return;
  }

  summaryNode.dataset.status = "failed";
  summaryNode.textContent = `${failedResults.length} JS unit tests failed.`;
  detailsNode.textContent = failedResults
    .map((item) => `${item.name}\n${item.message || "Unknown failure."}`)
    .join("\n\n");
}

async function run() {
  const harnessFactory = window.TimePollTestHarness && window.TimePollTestHarness.createHarness;
  const registerUnitTests = window.registerTimePollLogicUnitTests;

  if (typeof harnessFactory !== "function" || typeof registerUnitTests !== "function") {
    throw new Error("JS unit test harness scripts failed to load.");
  }

  const harness = harnessFactory();
  registerUnitTests(harness);
  const results = await harness.run();
  renderResults(results);
}

run().catch((error) => {
  const summaryNode = document.getElementById("summary");
  const detailsNode = document.getElementById("details");
  if (summaryNode) {
    summaryNode.dataset.status = "failed";
    summaryNode.textContent = "JS unit test runner crashed.";
  }
  if (detailsNode) {
    detailsNode.textContent = error && error.stack ? error.stack : String(error);
  }
});
