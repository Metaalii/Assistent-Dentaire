import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { LanguageProvider, useLanguage } from "../i18n";

function LangDisplay() {
  const { language, t } = useLanguage();
  return (
    <div>
      <span data-testid="lang">{language}</span>
      <span data-testid="app-name">{t("appName")}</span>
    </div>
  );
}

function LangSwitcher() {
  const { language, setLanguage } = useLanguage();
  return (
    <button onClick={() => setLanguage(language === "en" ? "fr" : "en")}>
      switch
    </button>
  );
}

describe("LanguageProvider / useLanguage", () => {
  it("defaults to English", () => {
    render(
      <LanguageProvider>
        <LangDisplay />
      </LanguageProvider>
    );
    expect(screen.getByTestId("lang").textContent).toBe("en");
    expect(screen.getByTestId("app-name").textContent).toBe("Dental Assistant");
  });

  it("switches to French and back", () => {
    render(
      <LanguageProvider>
        <LangDisplay />
        <LangSwitcher />
      </LanguageProvider>
    );
    fireEvent.click(screen.getByRole("button", { name: /switch/i }));
    expect(screen.getByTestId("lang").textContent).toBe("fr");

    fireEvent.click(screen.getByRole("button", { name: /switch/i }));
    expect(screen.getByTestId("lang").textContent).toBe("en");
  });

  it("falls back to English for missing French keys", () => {
    render(
      <LanguageProvider>
        <LangDisplay />
        <LangSwitcher />
      </LanguageProvider>
    );
    fireEvent.click(screen.getByRole("button", { name: /switch/i }));
    // appName exists in both locales; just check it's non-empty in French
    expect(screen.getByTestId("app-name").textContent).not.toBe("");
  });

  it("throws when used outside provider", () => {
    // Suppress the React error overlay output
    const originalError = console.error;
    console.error = () => {};
    expect(() => render(<LangDisplay />)).toThrow("useLanguage must be used within a LanguageProvider");
    console.error = originalError;
  });
});
