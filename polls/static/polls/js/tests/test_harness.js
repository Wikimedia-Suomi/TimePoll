function serializeValue(value) {
  return JSON.stringify(value, null, 2);
}

function normalizeObject(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeObject);
  }
  if (!value || typeof value !== "object") {
    return value;
  }

  const normalized = {};
  for (const key of Object.keys(value).sort()) {
    normalized[key] = normalizeObject(value[key]);
  }
  return normalized;
}

function createHarness() {
  const tests = [];

  function test(name, fn) {
    tests.push({ name, fn });
  }

  function assert(condition, message = "Assertion failed.") {
    if (!condition) {
      throw new Error(message);
    }
  }

  function assertEqual(actual, expected, message = "") {
    if (!Object.is(actual, expected)) {
      const detail = message ? `${message}\n` : "";
      throw new Error(`${detail}Expected ${serializeValue(expected)} but received ${serializeValue(actual)}.`);
    }
  }

  function assertDeepEqual(actual, expected, message = "") {
    const normalizedActual = normalizeObject(actual);
    const normalizedExpected = normalizeObject(expected);
    const actualSerialized = serializeValue(normalizedActual);
    const expectedSerialized = serializeValue(normalizedExpected);

    if (actualSerialized !== expectedSerialized) {
      const detail = message ? `${message}\n` : "";
      throw new Error(`${detail}Expected ${expectedSerialized} but received ${actualSerialized}.`);
    }
  }

  async function run() {
    const results = [];

    for (const item of tests) {
      try {
        await item.fn();
        results.push({ name: item.name, passed: true });
      } catch (error) {
        results.push({
          name: item.name,
          passed: false,
          message: error && error.message ? error.message : String(error)
        });
      }
    }

    return results;
  }

  return {
    test,
    assert,
    assertEqual,
    assertDeepEqual,
    run
  };
}

window.TimePollTestHarness = {
  createHarness
};
