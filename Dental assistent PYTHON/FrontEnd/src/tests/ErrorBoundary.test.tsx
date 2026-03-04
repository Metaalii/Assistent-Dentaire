import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ErrorBoundary from "../components/ErrorBoundary";
import { LanguageProvider } from "../i18n";

// Suppress expected console.error output from error boundary during tests
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

// Component that throws on render
function BrokenComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test render error");
  return <div>OK</div>;
}

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <Wrapper>
        <ErrorBoundary>
          <div>child content</div>
        </ErrorBoundary>
      </Wrapper>
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
  });

  it("shows fallback UI when a child throws", () => {
    render(
      <Wrapper>
        <ErrorBoundary>
          <BrokenComponent shouldThrow />
        </ErrorBoundary>
      </Wrapper>
    );
    // The error fallback contains 'Try Again' button
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("renders a custom fallback when provided", () => {
    render(
      <Wrapper>
        <ErrorBoundary fallback={<div>custom fallback</div>}>
          <BrokenComponent shouldThrow />
        </ErrorBoundary>
      </Wrapper>
    );
    expect(screen.getByText("custom fallback")).toBeInTheDocument();
  });

  it("recovers after clicking Try Again", () => {
    const { rerender } = render(
      <Wrapper>
        <ErrorBoundary>
          <BrokenComponent shouldThrow />
        </ErrorBoundary>
      </Wrapper>
    );
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    // After retry the boundary resets; re-render with a non-throwing child
    rerender(
      <Wrapper>
        <ErrorBoundary>
          <BrokenComponent shouldThrow={false} />
        </ErrorBoundary>
      </Wrapper>
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  it("calls onError callback when a child throws", () => {
    const onError = vi.fn();
    render(
      <Wrapper>
        <ErrorBoundary onError={onError}>
          <BrokenComponent shouldThrow />
        </ErrorBoundary>
      </Wrapper>
    );
    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
  });
});
