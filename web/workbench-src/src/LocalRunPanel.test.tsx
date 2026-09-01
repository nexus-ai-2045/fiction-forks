import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LocalRunPanel } from "./LocalRunPanel";

const readyHealth = {
  status: "ready",
  schema_version: "fiction_forks_local_run_response.v1",
  providers: ["fixture"],
  catalog_id: "japan-2036-preview-templates",
  catalog_version: 3,
  templates: [
    {
      template_id: "public-tools-access.v1",
      template_version: 3,
      scenario_id: "japan-2036-centralization",
      intervention_id: "doraemon-public-tools",
      intervention_sha256: "2e116cde3f8ad9547261cc58fd1b88c594f8bbefcc0d34961687dc47d21cf455",
      abstract_function: "高度な道具へのアクセスを監査可能な公共基盤として広げる",
      allowed_seeds: [2036],
      delay_profiles: ["none"],
    },
    {
      template_id: "contested-world-observation.v1",
      template_version: 3,
      scenario_id: "japan-2036-centralization",
      intervention_id: "haruhi-world-observation",
      intervention_sha256: "6b9420240ae02129b4fd24f679aef0a9e79dbd53dca052f58700e1a7d5c79d70",
      abstract_function: "複数の独立観測と異議申立てで世界状態の変化を検証する",
      allowed_seeds: [2036],
      delay_profiles: ["none"],
    },
  ],
};

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
      json: async () => readyHealth,
    }));
    render(<LocalRunPanel />);
    const run = screen.getByRole("button", { name: "シミュレーションを実行" });
    expect(run).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Session token"), { target: { value: "test-token" } });
    await waitFor(() => expect(run).toBeEnabled());
    expect(screen.getByLabelText("世界線template")).toHaveValue("contested-world-observation.v1");
  });

  it("fails closed when health carries no preview template projection", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ready", providers: ["fixture"] }),
    }));
    render(<LocalRunPanel />);
    await waitFor(() => expect(screen.getByText(/ローカルadapterに接続できません/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "シミュレーションを実行" })).toBeDisabled();
  });
});
