import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Profile } from "../lib/api";
import { ProfileList } from "./ProfileList";

const profile: Profile = {
  id: "abc-123",
  name: "Test",
  fingerprint_seed: 12345,
  proxy: null,
  timezone: null,
  locale: null,
  platform: "windows",
  user_agent: null,
  screen_width: 1920,
  screen_height: 1080,
  gpu_vendor: null,
  gpu_renderer: null,
  hardware_concurrency: null,
  humanize: false,
  human_preset: "default",
  headless: false,
  geoip: false,
  clipboard_sync: true,
  auto_launch: false,
  color_scheme: null,
  launch_args: [],
  notes: null,
  user_data_dir: "/data/profiles/abc-123",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  tags: [],
  status: "stopped",
  cdp_url: null,
};

describe("ProfileList", () => {
  it("shows profile notes in the sidebar", () => {
    render(
      <ProfileList
        profiles={[{ ...profile, notes: "Customer account A" }]}
        selectedId={null}
        onSelect={vi.fn()}
        onCopy={vi.fn()}
        onNew={vi.fn()}
      />,
    );

    expect(screen.getByText("Customer account A")).not.toBeNull();
  });

  it("copies a profile from the context menu", () => {
    const onCopy = vi.fn();
    render(
      <ProfileList
        profiles={[profile]}
        selectedId={null}
        onSelect={vi.fn()}
        onCopy={onCopy}
        onNew={vi.fn()}
      />,
    );

    fireEvent.contextMenu(screen.getByText("Test").closest("button")!);
    fireEvent.click(screen.getByText("Copy"));

    expect(onCopy).toHaveBeenCalledWith("abc-123");
  });
});
