import { fireEvent, render, screen, within } from "@testing-library/react";
import { App, describeForkOutcome, interventionDisplayName } from "./App";
import { comparison, describeActivationDelay, intervention } from "./data";

describe("workbench projection", () => {
  it("switches only between canonical named profiles", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "想像力で、破滅ルートをひっくり返せ。" })).toBeInTheDocument();
    expect(screen.getByText("アニメや物語のアイデアを、再現できる世界線シミュレーションへ。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "検証済み世界線を比較する" })).toHaveAttribute("href", "#comparison");
    expect(screen.getByRole("link", { name: "自分のアイデアを持ち込む" })).toHaveAttribute("href", "../");
    expect(screen.getByText(/破滅条件を倒すまで、世界線を何度でも組み替える/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "同じ2036年、二つの世界" })).toBeInTheDocument();
    expect(screen.getByText("2036年に修復不能条件へ到達。")).toBeInTheDocument();
    expect(screen.getByText(/生活基盤は通常介入で5ポイント悪化/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "制度の遅延が、発動を5年遅らせる。" })).toBeInTheDocument();
    const forkCard = screen.getByRole("article", { name: "介入世界" });
    expect(within(forkCard).getByText(`FORK / ${interventionDisplayName}`)).toBeInTheDocument();
    expect(within(forkCard).queryByText(new RegExp(intervention.extracted_function))).not.toBeInTheDocument();
    expect(interventionDisplayName).toBe("みんなで世界を観測する力");
    expect(screen.getByText("FIXTURE = 台本入力による決定論比較。AIの生成ではありません。")).toBeInTheDocument();
    expect(screen.getByText(/named profile（検証済み遅延条件）だけを切り替えます/)).toBeInTheDocument();
    expect(screen.getByText("2032年に発動し、2036年の比較時点で破滅条件を回避。")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/証拠来歴と対立仮説の公開検証手続を5年遅延/));
    expect(screen.getByText("発動が2037年となり、2036年の破滅条件に間に合いません。")).toBeInTheDocument();
    expect(screen.getAllByText("◆ 修復不能条件")).toHaveLength(3);
  });

  it("frames the verified Vertex miss as the next worldline to beat", () => {
    render(<App />);
    expect(screen.getByText(/AIの選択 → 3行動を安全に棄却/)).toHaveTextContent("発動2037年");
  });

  it("opens provenance and exposes fixture metadata", () => {
    render(<App />);
    const trigger = screen.getByRole("button", { name: /根拠と限界を開く/ });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "この比較の根拠と限界" });
    expect(dialog).toHaveTextContent("fiction_forks_comparison.v1");
    expect(dialog).toHaveTextContent("AI実測ではない");
    expect(dialog).toHaveTextContent("fixture replay同値検証済み");
    expect(dialog).toHaveTextContent(intervention.extracted_function);
    expect(dialog).toHaveTextContent(/5f3f88f[0-9a-f]+/);
    fireEvent.keyDown(dialog, { key: "Escape" });
    return new Promise<void>((resolve) => requestAnimationFrame(() => {
      expect(trigger).toHaveFocus();
      resolve();
    }));
  });

  it("does not overstate replay evidence for the delay profile", () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText(/証拠来歴と対立仮説の公開検証手続を5年遅延/));
    fireEvent.click(screen.getByRole("button", { name: /根拠と限界を開く/ }));
    expect(screen.getByRole("dialog")).toHaveTextContent("canonical digest検証済み（replay未検証）");
  });

  it("describes both critical and slack delays from activation evidence", () => {
    expect(describeActivationDelay("制度", 2032, 2037)).toBe("制度の遅延が、発動を5年遅らせる。");
    expect(describeActivationDelay("技術", 2032, 2032)).toBe("技術を遅らせても、発動年は変わらない。");
  });

  it("does not confuse late activation with an ineffective active intervention", () => {
    const activeButCollapsed = {
      ...comparison,
      fork: { ...comparison.fork, activation_year: 2032, collapse_year: 2036, collapsed: true },
    };
    expect(describeForkOutcome(activeButCollapsed)).toEqual({
      status: "介入後も破滅条件に到達",
      summary: "2032年に発動しましたが、2036年に修復不能条件へ到達。",
    });
  });
});
