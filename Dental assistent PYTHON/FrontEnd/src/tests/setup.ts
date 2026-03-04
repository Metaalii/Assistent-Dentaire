import "@testing-library/jest-dom";

// Stub Tauri invoke so unit tests run outside the desktop shell
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockRejectedValue(new Error("Tauri not available")),
}));
