const fs = require('fs');
const assert = require('assert/strict');

const detail = fs.readFileSync('archive/2026-09-05/index.html', 'utf8');
const overview = fs.readFileSync('archive/index.html', 'utf8');

assert.match(detail, /狼之诱惑/);
assert.match(detail, /码头连环凶杀案/);
assert.match(overview, /archive\/2026-09-05\//);
