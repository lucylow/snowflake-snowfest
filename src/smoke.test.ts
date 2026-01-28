import { describe, expect, it } from "vitest";

import App from "./App";

describe("app smoke", () => {
  it("can import App", () => {
    expect(App).toBeTruthy();
  });
});
