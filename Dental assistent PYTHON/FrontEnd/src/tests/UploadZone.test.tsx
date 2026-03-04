import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { createRef } from "react";
import UploadZone from "../components/dashboard/UploadZone";
import { LanguageProvider } from "../i18n";

function Wrapper({ children }: { children: React.ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

function renderUploadZone(overrides: Partial<React.ComponentProps<typeof UploadZone>> = {}) {
  const inputRef = createRef<HTMLInputElement>();
  const props = {
    onFileSelect: vi.fn(),
    fileName: null,
    isLoading: false,
    isDragActive: false,
    onDragOver: vi.fn(),
    onDragLeave: vi.fn(),
    onDrop: vi.fn(),
    inputRef,
    ...overrides,
  };
  return { ...render(<Wrapper><UploadZone {...props} /></Wrapper>), props };
}

describe("UploadZone", () => {
  it("renders the upload title", () => {
    renderUploadZone();
    expect(screen.getByRole("button", { name: /upload audio recording/i })).toBeInTheDocument();
  });

  it("shows 'Drop audio here' title when drag is active", () => {
    renderUploadZone({ isDragActive: true });
    expect(screen.getByText(/drop audio here/i)).toBeInTheDocument();
  });

  it("shows the selected file name when provided", () => {
    renderUploadZone({ fileName: "consult.wav" });
    expect(screen.getByText("consult.wav")).toBeInTheDocument();
  });

  it("calls onFileSelect when a file is picked via the input", () => {
    const { props } = renderUploadZone();
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
    const file = new File(["audio"], "test.mp3", { type: "audio/mpeg" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(props.onFileSelect).toHaveBeenCalledWith(file);
  });

  it("calls onDrop when a file is dropped", () => {
    const { props } = renderUploadZone();
    const dropZone = screen.getByRole("button", { name: /upload audio recording/i });
    const mockEvent = new Event("drop", { bubbles: true });
    fireEvent(dropZone, mockEvent);
    expect(props.onDrop).toHaveBeenCalled();
  });

  it("applies disabled styles when loading", () => {
    renderUploadZone({ isLoading: true });
    // When loading the card wrapper gets opacity-50 + pointer-events-none
    // Test that the 'Choose Audio File' button is disabled
    expect(screen.getByRole("button", { name: /choose audio file/i })).toBeDisabled();
  });

  it("shows all supported file format badges", () => {
    renderUploadZone();
    for (const ext of ["WAV", "MP3", "M4A", "OGG", "WEBM", "MP4"]) {
      expect(screen.getByText(ext)).toBeInTheDocument();
    }
  });
});
