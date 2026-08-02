import { readFileSync } from "fs";
import { getBytes, ref, uploadBytes } from "firebase/storage";
import { afterAll, beforeAll, describe, it } from "vitest";
import { assertFails, assertSucceeds, initializeTestEnvironment } from "@firebase/rules-unit-testing";

let testEnv;

// Minimal gzip magic bytes — the rule checks contentType/size/filename, not
// that the payload is a valid archive, so this is sufficient.
const gzipBytes = new Uint8Array([0x1f, 0x8b, 0x08, 0x00]);

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: "mri-analysis-rules-test",
    storage: {
      rules: readFileSync("../storage.rules", "utf8"),
      host: "127.0.0.1",
      port: 9199,
    },
  });
});

afterAll(async () => {
  await testEnv.cleanup();
});

describe("storage.rules — uploads/{fileName}", () => {
  it("allows a correctly-typed, correctly-named upload", async () => {
    const unauth = testEnv.unauthenticatedContext();
    const fileRef = ref(unauth.storage(), "uploads/job123.nii.gz");
    await assertSucceeds(uploadBytes(fileRef, gzipBytes, { contentType: "application/gzip" }));
  });

  it("denies upload with the wrong content type", async () => {
    const unauth = testEnv.unauthenticatedContext();
    const fileRef = ref(unauth.storage(), "uploads/job123.nii.gz");
    await assertFails(uploadBytes(fileRef, gzipBytes, { contentType: "application/octet-stream" }));
  });

  it("denies upload with a non-.nii.gz filename", async () => {
    const unauth = testEnv.unauthenticatedContext();
    const fileRef = ref(unauth.storage(), "uploads/job123.exe");
    await assertFails(uploadBytes(fileRef, gzipBytes, { contentType: "application/gzip" }));
  });

  it("denies a client read of an uploaded file (backend-only reads)", async () => {
    const unauth = testEnv.unauthenticatedContext();
    const fileRef = ref(unauth.storage(), "uploads/readback-check.nii.gz");
    await assertSucceeds(uploadBytes(fileRef, gzipBytes, { contentType: "application/gzip" }));
    await assertFails(getBytes(fileRef));
  });
});

describe("storage.rules — default deny", () => {
  it("denies writes to any path outside uploads/", async () => {
    const unauth = testEnv.unauthenticatedContext();
    const fileRef = ref(unauth.storage(), "other/job123.nii.gz");
    await assertFails(uploadBytes(fileRef, gzipBytes, { contentType: "application/gzip" }));
  });
});
