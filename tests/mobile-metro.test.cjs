const assert = require("node:assert/strict");
const {readFileSync, mkdtempSync, mkdirSync, writeFileSync, rmSync} = require("node:fs");
const {tmpdir} = require("node:os");
const {createRequire} = require("node:module");
const {spawnSync} = require("node:child_process");
const path = require("node:path");
const test = require("node:test");

const mobileRequire = createRequire(path.resolve(__dirname, "../mobile/package.json"));
const {getAssetSize, getAssetData} = mobileRequire("metro/private/Assets");

test("patched Metro still reads Lazuna's PNG asset and rejects empty images", async () => {
  const iconPath = path.resolve(__dirname, "../mobile/assets/icon.png");
  const bytes = readFileSync(iconPath);
  const expected = {width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20)};
  assert.deepEqual(getAssetSize("png", bytes, iconPath), expected);
  const asset = await getAssetData(iconPath, "assets/icon.png", [], "android", "/assets");
  assert.equal(asset.width, expected.width);
  assert.equal(asset.height, expected.height);
  assert.throws(() => getAssetSize("png", Buffer.alloc(0), "empty.png"));
});

test("Metro rejects an ICNS zero-length chunk disguised as PNG without looping", () => {
  // Bound a synchronous parser regression in a separate process so an accidental
  // reintroduction of the affected reader cannot hang the whole test runner.
  const source = `
    const assert = require('node:assert/strict');
    const {getAssetSize} = require('metro/private/Assets');
    const input = Buffer.alloc(16);
    input.write('icns', 0);
    input.writeUInt32BE(16, 4);
    input.write('ic07', 8);
    input.writeUInt32BE(0, 12);
    assert.throws(() => getAssetSize('png', input, 'disguised.png'));
  `;
  const result = spawnSync(process.execPath, ["-e", source], {
    cwd: path.resolve(__dirname, "../mobile"), timeout: 3000, maxBuffer: 4096, encoding: "utf8",
  });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
});

test("Expo native file discovery and fingerprint exclusions preserve their contracts", async (t) => {
  const root = mkdtempSync(path.join(tmpdir(), "lazuna-expo-path-"));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const directory = path.join(root, "android/app/src/main/java/com/example");
  mkdirSync(directory, {recursive: true});
  writeFileSync(path.join(directory, "MainApplication.kt"), "// temporary Kotlin fixture");
  const {getMainApplicationAsync} = mobileRequire("@expo/config-plugins/build/android/Paths");
  const file = await getMainApplicationAsync(root);
  assert.equal(file.path, path.join(directory, "MainApplication.kt"));
  assert.equal(file.language, "kt");
  const {isIgnoredPath} = mobileRequire("@expo/fingerprint/build/utils/Path");
  assert.equal(isIgnoredPath(".expo/cache/file", [".expo/**"]), true);
  assert.equal(isIgnoredPath("assets/icon.png", ["assets/**", "!assets/icon.png"]), false);
  assert.equal(isIgnoredPath("assets/private.png", ["assets/**", "!assets/icon.png"]), true);
});
