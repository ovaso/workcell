#!/usr/bin/env node

import assert from "node:assert/strict";
import { validateValue } from "../scripts/validate-schema-examples.mjs";

/** 返回一个简单 Schema 对给定值的校验错误。 */
function errorsFor(value, schema) {
  const errors = [];
  validateValue(value, schema, schema, "$", errors);
  return errors;
}

assert.deepEqual(errorsFor("READY", { enum: ["READY", "PAUSED"] }), []);
assert.ok(errorsFor("UNKNOWN", { enum: ["READY", "PAUSED"] }).length > 0);
assert.ok(errorsFor({}, { type: "object", required: ["id"] }).length > 0);
assert.ok(errorsFor("anything", false).length > 0);
assert.ok(errorsFor("bad-date", { type: "string", format: "date-time" }).length > 0);
assert.ok(errorsFor("/absolute", { not: { pattern: "^/" } }).length > 0);
assert.deepEqual(errorsFor("relative/path", { not: { pattern: "^/" } }), []);

process.stdout.write("Schema validator negative checks passed.\n");
