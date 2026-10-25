import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LocalRunPanel } from "./LocalRunPanel";
import { requestLocalRun } from "./run-request";

vi.mock("./run-request", async () => {
  const actual = await vi.importActual<typeof import("./run-request")>("./run-request");
  return {
    ...actual,
    requestLocalRun: vi.fn(),
  };
});

vi.mock("./Replay", () => ({
  ReplaySection: () => <div data-testid="replay-stub" />,
}));

const mockedRequestLocalRun = vi.mocked(requestLocalRun);

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
  afterEach(() => {
    vi.unstubAllGlobals();
    mockedRequestLocalRun.mockReset();
  });

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

describe("template selection discards stale run state", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    mockedRequestLocalRun.mockReset();
  });

  it("discards verified results when the template changes", async () => {
    mockedRequestLocalRun.mockResolvedValue({
      run_id: "ff-stale",
      execution_id: "ffx-" + "a".repeat(32),
      replay: { events: [{ type: "x" }, { type: "y" }] },
      bundle: {
        run_request: {
          parameters: { intervention_id: "haruhi-world-observation" },
        },
      },
    } as never);

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => readyHealth,
    }));
    render(<LocalRunPanel />);
    fireEvent.change(screen.getByLabelText("Session token"), { target: { value: "test-token" } });
    const run = screen.getByRole("button", { name: "シミュレーションを実行" });
    await waitFor(() => expect(run).toBeEnabled());
    fireEvent.click(run);
    await waitFor(() => expect(screen.getByText(/検証成功/)).toBeInTheDocument());
    expect(screen.getByText(/run_id ff-stale/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("世界線template"), {
      target: { value: "public-tools-access.v1" },
    });
    await waitFor(() => {
      expect(screen.queryByText(/検証成功/)).not.toBeInTheDocument();
      expect(screen.queryByText(/run_id ff-stale/)).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText("世界線template")).toHaveValue("public-tools-access.v1");
    expect(screen.getByText(/SHA-256 2e116cde3f8ad9547261cc58fd1b88c594f8bbefcc0d34961687dc47d21cf455/)).toBeInTheDocument();
  });

  it("ignores a late response after the template changes during a pending run", async () => {
    let resolveRun: (value: never) => void = () => undefined;
    mockedRequestLocalRun.mockImplementation(
      () => new Promise((resolve) => { resolveRun = resolve as (value: never) => void; }),
    );

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => readyHealth,
    }));
    render(<LocalRunPanel />);
    fireEvent.change(screen.getByLabelText("Session token"), { target: { value: "test-token" } });
    const run = screen.getByRole("button", { name: "シミュレーションを実行" });
    await waitFor(() => expect(run).toBeEnabled());
    fireEvent.click(run);
    await waitFor(() => expect(run).toHaveTextContent("実行中…"));

    fireEvent.change(screen.getByLabelText("世界線template"), {
      target: { value: "public-tools-access.v1" },
    });
    await waitFor(() => expect(run).toHaveTextContent("シミュレーションを実行"));

    resolveRun({
      run_id: "ff-late",
      execution_id: "ffx-" + "b".repeat(32),
      replay: { events: [{ type: "x" }] },
      bundle: {
        run_request: {
          parameters: { intervention_id: "haruhi-world-observation" },
        },
      },
    } as never);

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText(/検証成功/)).not.toBeInTheDocument();
    expect(screen.queryByText(/run_id ff-late/)).not.toBeInTheDocument();
    expect(run).not.toBeDisabled();
  });
});
