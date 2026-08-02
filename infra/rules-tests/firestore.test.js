import { readFileSync } from "fs";
import { doc, getDoc, setDoc } from "firebase/firestore";
import { afterAll, beforeAll, describe, it } from "vitest";
import { assertFails, assertSucceeds, initializeTestEnvironment } from "@firebase/rules-unit-testing";

let testEnv;

beforeAll(async () => {
  testEnv = await initializeTestEnvironment({
    projectId: "mri-analysis-rules-test",
    firestore: {
      rules: readFileSync("../firestore.rules", "utf8"),
      host: "127.0.0.1",
      port: 8080,
    },
  });
});

afterAll(async () => {
  await testEnv.cleanup();
});

describe("firestore.rules — jobs/{jobId}", () => {
  it("denies unauthenticated read", async () => {
    const unauth = testEnv.unauthenticatedContext();
    await assertFails(getDoc(doc(unauth.firestore(), "jobs/job123")));
  });

  it("denies read when the job_id claim does not match the document", async () => {
    const wrongClaim = testEnv.authenticatedContext("user1", { job_id: "other-job" });
    await assertFails(getDoc(doc(wrongClaim.firestore(), "jobs/job123")));
  });

  it("allows read when the job_id claim matches the document", async () => {
    const matching = testEnv.authenticatedContext("user1", { job_id: "job123" });
    await assertSucceeds(getDoc(doc(matching.firestore(), "jobs/job123")));
  });

  it("denies client writes even with a matching claim (backend-only via service account)", async () => {
    const matching = testEnv.authenticatedContext("user1", { job_id: "job123" });
    await assertFails(setDoc(doc(matching.firestore(), "jobs/job123"), { status: "queued" }));
  });
});

describe("firestore.rules — results/{jobId}", () => {
  it("denies read without a matching job_id claim", async () => {
    const unauth = testEnv.unauthenticatedContext();
    await assertFails(getDoc(doc(unauth.firestore(), "results/job123")));
  });

  it("allows read with a matching job_id claim", async () => {
    const matching = testEnv.authenticatedContext("user1", { job_id: "job123" });
    await assertSucceeds(getDoc(doc(matching.firestore(), "results/job123")));
  });
});

describe("firestore.rules — default deny", () => {
  it("denies read on an arbitrary unlisted collection, even when authenticated", async () => {
    const matching = testEnv.authenticatedContext("user1", { job_id: "job123" });
    await assertFails(getDoc(doc(matching.firestore(), "users/user1")));
  });
});
