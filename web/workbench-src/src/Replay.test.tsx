import { fireEvent, render, screen, within, act } from "@testing-library/react";
import { describeReplayEvent, ReplaySection } from "./Replay";
import { replayRun } from "./data";
import type { ReplayEvent } from "./types";

function currentEventCard() {
  return screen.getByRole("article", { name: /行動 \d+ \/ \d+/ });
}

describe("replay of the verified fixture run", () => {
  it("shows the stored events in stored order, starting at sequence 1", () => {
    render(<ReplaySection run={replayRun} />);
    expect(screen.getByText(/これは検証済みrunのreplayです/)).toBeInTheDocument();
    expect(replayRun.events.map((event) => event.sequence)).toEqual(
      replayRun.events.map((_, index) => index + 1),
    );
    const card = currentEventCard();
    const first = replayRun.events[0];
    expect(within(card).getByText(`行動 1 / ${replayRun.events.length}`)).toBeInTheDocument();
    expect(within(card).getByText(first.action.agent_id)).toBeInTheDocument();
    expect(within(card).getByText(first.action.action_id)).toBeInTheDocument();
    expect(within(card).getByText(/条件付き|支持|反対|棄権/)).toBeInTheDocument();
    expect(within(card).getByText(first.valid ? "VALID" : "REJECTED")).toBeInTheDocument();
    expect(within(card).getByText(first.event_hash)).toBeInTheDocument();
  });

  it("navigates with 次へ / 前へ / 最初 and the jump strip", () => {
    render(<ReplaySection run={replayRun} />);
    expect(screen.getByRole("button", { name: "前へ" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "次へ" }));
    expect(within(currentEventCard()).getByText(`行動 2 / ${replayRun.events.length}`)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "前へ" }));
    expect(within(currentEventCard()).getByText(`行動 1 / ${replayRun.events.length}`)).toBeInTheDocument();
    const last = replayRun.events.length;
    fireEvent.click(screen.getByRole("button", { name: new RegExp(`^行動${last}:`) }));
    expect(within(currentEventCard()).getByText(`行動 ${last} / ${last}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "次へ" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "最初" }));
    expect(within(currentEventCard()).getByText(`行動 1 / ${last}`)).toBeInTheDocument();
  });

  it("autoplays forward, stops on 停止, and stops at the final event", () => {
    vi.useFakeTimers();
    try {
      render(<ReplaySection run={replayRun} />);
      const play = screen.getByRole("button", { name: "自動再生" });
      const stop = screen.getByRole("button", { name: "停止" });
      expect(stop).toBeDisabled();
      fireEvent.click(play);
      expect(play).toBeDisabled();
      act(() => { vi.advanceTimersByTime(1800); });
      expect(within(currentEventCard()).getByText(`行動 2 / ${replayRun.events.length}`)).toBeInTheDocument();
      fireEvent.click(stop);
      act(() => { vi.advanceTimersByTime(10_000); });
      expect(within(currentEventCard()).getByText(`行動 2 / ${replayRun.events.length}`)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "自動再生" }));
      for (let step = 0; step < replayRun.events.length + 1; step += 1) {
        act(() => { vi.advanceTimersByTime(1800); });
      }
      expect(within(currentEventCard()).getByText(`行動 ${replayRun.events.length} / ${replayRun.events.length}`)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "停止" })).toBeDisabled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("announces the current event through the live region", () => {
    render(<ReplaySection run={replayRun} />);
    const first = replayRun.events[0];
    expect(screen.getByText(describeReplayEvent(first, replayRun.events.length))).toHaveAttribute("aria-live", "polite");
  });

  it("describes a rejected event without recomputing stored values", () => {
    const rejected: ReplayEvent = {
      sequence: 11,
      intent_id: "t3:civic_challenger",
      valid: false,
      invalid_reason: "missing responds_to",
      event_hash: "0".repeat(64),
      action: {
        schema_version: "fiction_forks_action.v1",
        run_id: replayRun.run_id,
        turn: 3,
        agent_id: "civic_challenger",
        action_id: "abstain",
        stance: "abstain",
        responds_to: [],
        target_ids: [],
      },
    };
    expect(describeReplayEvent(rejected, 15)).toBe(
      "行動 11 / 15: ターン3のcivic_challengerがabstainを選択（棄権）— 安全に棄却（missing responds_to）",
    );
  });
});
