import { fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";

describe("workbench projection", () => {
  it("switches only between canonical named profiles", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "同じ2036年、二つの世界" })).toBeInTheDocument();
    expect(screen.getByText("2032年に発動し、2036年の比較時点で破滅条件を回避。")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/異議申立て制度を5年遅延/));
    expect(screen.getByText("発動が2037年となり、2036年の破滅条件に間に合いません。")).toBeInTheDocument();
    expect(screen.getAllByText("◆ 修復不能条件")).toHaveLength(3);
  });

  it("opens provenance and exposes fixture metadata", () => {
    render(<App />);
    const trigger = screen.getByRole("button", { name: /根拠と限界を開く/ });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "この比較の根拠と限界" });
    expect(dialog).toHaveTextContent("fiction_forks_comparison.v1");
    expect(dialog).toHaveTextContent("AI実測ではない");
    expect(dialog).toHaveTextContent(/5f3f88f[0-9a-f]+/);
    fireEvent.keyDown(dialog, { key: "Escape" });
    return new Promise<void>((resolve) => requestAnimationFrame(() => {
      expect(trigger).toHaveFocus();
      resolve();
    }));
  });
});
