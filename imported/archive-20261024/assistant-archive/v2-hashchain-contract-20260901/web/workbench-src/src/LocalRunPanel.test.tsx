import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LocalRunPanel } from "./LocalRunPanel";

describe("local adapter health boundary", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("fails closed when a Pages fallback returns HTML-like health data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }));
    render(<LocalRunPanel />);
    const run = screen.getByRole("button", { name: "シミュレーションを実行" });
    await waitFor(() => expect(screen.getByText(/ローカルadapterに接続できません/)).toBeInTheDocument());
    expect(run).toBeDisabled();
  });

  it("enables fixture execution only after a valid ready health contract", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ready", providers: ["fixture"], worldlines: ["haruhi-world-observation"] }),
    }));
    render(<LocalRunPanel />);
    const run = screen.getByRole("button", { name: "シミュレーションを実行" });
    expect(run).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Session token"), { target: { value: "test-token" } });
    await waitFor(() => expect(run).toBeEnabled());
  });
});
