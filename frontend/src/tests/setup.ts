import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

import { resetPlayerStateForTests } from "../hooks/usePlayer";

afterEach(() => {
  resetPlayerStateForTests();
});
