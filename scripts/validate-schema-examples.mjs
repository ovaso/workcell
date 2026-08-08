#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, "..");
const schemaDirectory = path.join(repositoryRoot, "schemas");
const exampleDirectory = path.join(schemaDirectory, "examples");

/** Convert a JSON Pointer segment to an object key. */
function decodePointerSegment(segment) {
  return segment.replaceAll("~1", "/").replaceAll("~0", "~");
}

/** Resolve a local reference in the current schema. */
function resolveReference(rootSchema, reference) {
  if (!reference.startsWith("#/")) {
    throw new Error(`Only local schema references are supported: ${reference}`);
  }
  return reference
    .slice(2)
    .split("/")
    .map(decodePointerSegment)
    .reduce((value, key) => value[key], rootSchema);
}

/** Return whether a JavaScript value matches a basic JSON Schema type. */
function matchesType(value, expectedType) {
  switch (expectedType) {
    case "null":
      return value === null;
    case "array":
      return Array.isArray(value);
    case "object":
      return value !== null && typeof value === "object" && !Array.isArray(value);
    case "integer":
      return Number.isInteger(value);
    case "number":
      return typeof value === "number" && Number.isFinite(value);
    default:
      return typeof value === expectedType;
  }
}

/** Validate the ISO 8601 date-time forms used by this repository. */
function isDateTime(value) {
  return typeof value === "string"
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)
    && !Number.isNaN(Date.parse(value));
}

/** Validate a value recursively and append every error to errors. */
function validateValue(value, schema, rootSchema, location, errors) {
  if (schema === false) {
    errors.push(`${location}: value is forbidden`);
    return;
  }
  if (schema === true || Object.keys(schema).length === 0) {
    return;
  }
  if (schema.$ref) {
    validateValue(value, resolveReference(rootSchema, schema.$ref), rootSchema, location, errors);
  }
  for (const childSchema of schema.allOf ?? []) {
    validateValue(value, childSchema, rootSchema, location, errors);
  }
  if (schema.not) {
    const forbiddenMatchErrors = [];
    validateValue(value, schema.not, rootSchema, location, forbiddenMatchErrors);
    if (forbiddenMatchErrors.length === 0) {
      errors.push(`${location}: value matches a forbidden schema`);
    }
  }
  if (schema.const !== undefined && JSON.stringify(value) !== JSON.stringify(schema.const)) {
    errors.push(`${location}: expected constant ${JSON.stringify(schema.const)}`);
  }
  if (schema.enum && !schema.enum.some((item) => JSON.stringify(item) === JSON.stringify(value))) {
    errors.push(`${location}: value is not in enum`);
  }
  if (schema.type) {
    const expectedTypes = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!expectedTypes.some((expectedType) => matchesType(value, expectedType))) {
      errors.push(`${location}: expected type ${expectedTypes.join("|")}`);
      return;
    }
  }
  if (typeof value === "string") {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      errors.push(`${location}: string is shorter than ${schema.minLength}`);
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      errors.push(`${location}: string is longer than ${schema.maxLength}`);
    }
    if (schema.pattern && !(new RegExp(schema.pattern)).test(value)) {
      errors.push(`${location}: string does not match ${schema.pattern}`);
    }
    if (schema.format === "date-time" && !isDateTime(value)) {
      errors.push(`${location}: invalid date-time`);
    }
  }
  if (typeof value === "number" && schema.minimum !== undefined && value < schema.minimum) {
    errors.push(`${location}: number is below ${schema.minimum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      errors.push(`${location}: array has fewer than ${schema.minItems} items`);
    }
    if (schema.uniqueItems) {
      const serialized = value.map((item) => JSON.stringify(item));
      if (new Set(serialized).size !== serialized.length) {
        errors.push(`${location}: array items are not unique`);
      }
    }
    if (schema.items) {
      value.forEach((item, index) => validateValue(item, schema.items, rootSchema, `${location}[${index}]`, errors));
    }
  }
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    for (const requiredKey of schema.required ?? []) {
      if (!Object.hasOwn(value, requiredKey)) {
        errors.push(`${location}: missing required key ${requiredKey}`);
      }
    }
    if (schema.propertyNames) {
      for (const key of Object.keys(value)) {
        validateValue(key, schema.propertyNames, rootSchema, `${location} property name`, errors);
      }
    }
    const declaredProperties = schema.properties ?? {};
    for (const [key, childValue] of Object.entries(value)) {
      if (Object.hasOwn(declaredProperties, key)) {
        validateValue(childValue, declaredProperties[key], rootSchema, `${location}.${key}`, errors);
      } else if (schema.additionalProperties === false) {
        errors.push(`${location}: unexpected key ${key}`);
      } else if (schema.additionalProperties && typeof schema.additionalProperties === "object") {
        validateValue(childValue, schema.additionalProperties, rootSchema, `${location}.${key}`, errors);
      }
    }
  }
}

/** Read a schema/example pair and validate it without dependencies. */
function validatePair(baseName) {
  const schemaPath = path.join(schemaDirectory, `${baseName}.schema.json`);
  const examplePath = path.join(exampleDirectory, `${baseName}.example.json`);
  const rootSchema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
  const example = JSON.parse(fs.readFileSync(examplePath, "utf8"));
  const errors = [];
  validateValue(example, rootSchema, rootSchema, "$", errors);
  if (errors.length > 0) {
    throw new Error(`${baseName} failed:\n${errors.map((error) => `  - ${error}`).join("\n")}`);
  }
}

/** Validate every schema/example pair in the repository. */
function main() {
  const schemaNames = fs.readdirSync(schemaDirectory)
    .filter((name) => name.endsWith(".schema.json"))
    .map((name) => name.replace(/\.schema\.json$/, ""))
    .sort();

  for (const schemaName of schemaNames) {
    validatePair(schemaName);
  }

  process.stdout.write(`Validated ${schemaNames.length} schema example pairs.\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}

export { validateValue };
