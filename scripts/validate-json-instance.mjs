#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";
import { validateValue } from "./validate-schema-examples.mjs";

/** 打印命令用法并以参数错误退出。 */
function usage() {
  process.stderr.write("Usage: validate-json-instance.mjs <schema.json> <instance.json>\n");
  process.exit(2);
}

if (process.argv.length !== 4) {
  usage();
}

const schemaPath = process.argv[2];
const instancePath = process.argv[3];
const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const instance = JSON.parse(fs.readFileSync(instancePath, "utf8"));
const errors = [];

validateValue(instance, schema, schema, "$", errors);
if (errors.length > 0) {
  process.stderr.write(`${errors.map((error) => `ERROR: ${error}`).join("\n")}\n`);
  process.exit(1);
}

process.stdout.write(`VALID: ${instancePath}\n`);
