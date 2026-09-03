import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

type FetchResponse = {
  json: () => Promise<unknown>;
  ok: boolean;
  status?: number;
};

function buildSettingsPayload(overrides: Record<string, unknown> = {}) {
  return {
    default_live_voice_id: "builtin:kokoro:af-sarah",
    default_export_voice_id: "preset:11",
    fallback_voice_id: "builtin:piper:fast-reader",
    selected_clone_model_engine: "qwen3_clone_0_6b",
    engine_statuses: [
      {
        engine: "kokoro",
        display_name: "Natural reader",
        availability: "available",
        availability_detail: "Kokoro is ready with 6 built-in voices.",
        supports_live_reading: true,
        supports_export: true,
        engine_family: "kokoro",
        model_name: "Kokoro-82M ONNX",
        voice_count: 6,
      },
      {
        engine: "piper",
        display_name: "Fast reader",
        availability: "available",
        availability_detail: "Piper is ready with 1 local voice.",
        supports_live_reading: true,
        supports_export: true,
        engine_family: "piper",
        model_name: null,
        voice_count: 1,
      },
    ],
    host_runtime: {
      host_name: "Server",
      runtime_label: "Server GPU host",
      gpu_name: "NVIDIA GeForce RTX 3080",
      execution_summary: "This host is serving Open Choice Reader and performing audio generation here.",
    },
    clone_runtime: {
      engine: "qwen3_clone",
      model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
      preset_count: 1,
      availability: "available",
      availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
      usage_summary:
        "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
      execution_summary:
        "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
      available_models: [
        {
          engine: "qwen3_clone_0_6b",
          display_name: "Premium clone 0.6B",
          model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          availability: "available",
          availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
        },
        {
          engine: "qwen3_clone_1_7b",
          display_name: "Premium clone 1.7B",
          model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
          availability: "available",
          availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
        },
      ],
    },
    ...overrides,
  };
}

describe("VoicesPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let playMock: ReturnType<typeof vi.fn>;
  let pauseMock: ReturnType<typeof vi.fn>;
  let createObjectUrlMock: ReturnType<typeof vi.fn>;
  let revokeObjectUrlMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: "builtin:kokoro:af-sarah",
              name: "Sarah",
              voice_type: "built_in",
              engine: "kokoro",
              engine_family: "kokoro",
              mode_label: "Natural reader",
              description: "Higher-quality local Kokoro narrator for primary live reading.",
              availability: "available",
              availability_detail: "Kokoro is ready with 6 built-in voices.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: "Kokoro-82M ONNX",
            },
            {
              id: "builtin:piper:fast-reader",
              name: "Fast Reader",
              voice_type: "built_in",
              engine: "piper",
              engine_family: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: null,
            },
          ],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    playMock = vi.fn(function play(this: HTMLMediaElement) {
      this.dispatchEvent(new Event("play"));
      return Promise.resolve();
    });
    pauseMock = vi.fn(function pause(this: HTMLMediaElement) {
      this.dispatchEvent(new Event("pause"));
    });
    createObjectUrlMock = vi.fn(() => "blob:voice-preview");
    revokeObjectUrlMock = vi.fn();

    Object.defineProperty(window.HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: playMock,
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: pauseMock,
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectUrlMock,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectUrlMock,
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("lists voice presets for the voices route", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: "builtin:kokoro:af-sarah",
              name: "Sarah",
              voice_type: "built_in",
              engine: "kokoro",
              engine_family: "kokoro",
              mode_label: "Natural reader",
              description: "Higher-quality local Kokoro narrator for primary live reading.",
              availability: "available",
              availability_detail: "Kokoro is ready with 6 built-in voices.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: "Kokoro-82M ONNX",
            },
            {
              id: "builtin:piper:fast-reader",
              name: "Fast Reader",
              voice_type: "built_in",
              engine: "piper",
              engine_family: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: null,
            },
            {
              id: "preset:11",
              name: "Alice Reader",
              voice_type: "cloned",
              engine: "qwen3_clone",
              engine_family: "qwen3_clone",
              mode_label: "Cloned voice",
              description: "Saved reference voice preset for premium live reading and audiobook export.",
              availability: "available",
              availability_detail: "Qwen3 clone live reading and exports are ready when a saved preset is selected.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: "A calm, warm speaking sample for audiobook export.",
              model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            },
          ],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: 11,
              name: "Alice Reader",
              engine: "qwen",
              transcript: "A calm, warm speaking sample for audiobook export.",
            },
          ],
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Voices",
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Current defaults")).toBeInTheDocument();
    expect(screen.getByText("Default live narrator")).toBeInTheDocument();
    expect(screen.getByText("Default export narrator")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Built-in narrator shelves" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cloned narrators" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clone a new voice" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save voice defaults" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save cloned voice" })).toBeInTheDocument();
    expect(await screen.findByText("Fast Reader")).toBeInTheDocument();
    expect(screen.getAllByText("Sarah").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Kokoro narrators" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Piper narrators" })).toBeInTheDocument();
    expect(screen.getAllByText("Premium clone 0.6B").length).toBeGreaterThan(0);
    expect(screen.getByText("Premium clone 1.7B")).toBeInTheDocument();
    expect(await screen.findByText("1 cloned presets")).toBeInTheDocument();
    const presetsList = screen.getByRole("list", { name: "Saved voice presets" });
    expect(within(presetsList).getByText("Alice Reader")).toBeInTheDocument();
    expect(within(presetsList).getByText("Cloned voice")).toBeInTheDocument();
    expect(within(presetsList).getByText(/Live \+ Export/)).toBeInTheDocument();
    expect(within(presetsList).getByText(/A calm, warm speaking sample/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview narrator Sarah" })).toBeInTheDocument();
    expect(within(presetsList).getByRole("button", { name: "Preview narrator Alice Reader" })).toBeInTheDocument();
  });

  it("plays an audible narrator preview without changing the saved default first", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: "builtin:kokoro:af-sarah",
              name: "Sarah",
              voice_type: "built_in",
              engine: "kokoro",
              engine_family: "kokoro",
              mode_label: "Natural reader",
              description: "Higher-quality local Kokoro narrator for primary live reading.",
              availability: "available",
              availability_detail: "Kokoro is ready with 6 built-in voices.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: "Kokoro-82M ONNX",
            },
          ],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (
        typeof input === "string" &&
        input === "/api/voices/preview?voice_option_id=builtin%3Akokoro%3Aaf-sarah" &&
        !init
      ) {
        return Promise.resolve({
          ok: true,
          status: 200,
          blob: async () => new Blob(["RIFFpreview"], { type: "audio/wav" }),
        });
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Preview narrator Sarah" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/voices/preview?voice_option_id=builtin%3Akokoro%3Aaf-sarah");
    });
    await waitFor(() => {
      expect(playMock).toHaveBeenCalledTimes(1);
    });
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Previewing Sarah on Natural reader | Kokoro-82M ONNX")).toBeInTheDocument();
    expect(screen.getByText("Default live narrator")).toBeInTheDocument();
    expect(screen.getAllByText("Sarah").length).toBeGreaterThan(0);
  });

  it("shows explicit empty states when no built-in or cloned voices are available yet", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && (input === "/api/voices/options" || input === "/api/voices/presets")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload({
            default_live_voice_id: "",
            default_export_voice_id: "",
            fallback_voice_id: null,
            clone_runtime: {
              ...buildSettingsPayload().clone_runtime,
              available_models: [],
            },
          }),
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Built-in narrator shelves" })).toBeInTheDocument();
    expect(screen.getByText("No built-in reader voices are available on this host right now.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cloned narrators" })).toBeInTheDocument();
    expect(screen.getByText("No cloned voices saved yet. Upload a reference clip below to create the first cloned narrator.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create first cloned voice" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clone a new voice" })).toBeInTheDocument();
  });

  it("renders nullable transcript values without crashing the voices list", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: 11,
              name: "Narrator Null Transcript",
              engine: "qwen3_clone",
              transcript: null,
            },
          ],
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const presetsList = await screen.findByRole("list", { name: "Saved voice presets" });
    expect(within(presetsList).getByText("Narrator Null Transcript")).toBeInTheDocument();
    expect(within(presetsList).getByText("No transcript saved.")).toBeInTheDocument();
  });

  it("transcribes an uploaded reference clip into the clone transcript field before saving", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/transcribe-reference" && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);
        expect((init.body as FormData).get("reference_audio")).toBeInstanceOf(File);

        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            transcript: "Automatically drafted local transcript.",
            language: "en",
            engine: "faster-whisper:base",
            segments: [],
          }),
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });
    fireEvent.change(await screen.findByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Transcribe audio" }));

    expect(await screen.findByRole("button", { name: "Transcribing audio..." })).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByLabelText("Transcript")).toHaveValue("Automatically drafted local transcript.");
    });
    expect(screen.getByText("Transcript draft is ready to review.")).toBeInTheDocument();
  });

  it("searches public voice samples and imports the reviewed transcript into clone presets", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/clone-samples/search?q=ada&limit=10") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            query: "ada",
            items: [
              {
                id: "sample-1",
                provider: "librivox",
                title: "Public Domain Reading - Chapter 1",
                speaker: "Ada Reader",
                audio_url: "https://archive.org/download/sample/chapter1.mp3",
                transcript: null,
                transcript_source_url: "https://www.gutenberg.org/ebooks/123",
                source_url: "https://librivox.org/public-domain-reading/",
                license_label: "Public domain",
                provenance_note: "Review the transcript before importing.",
                is_importable: true,
              },
            ],
          }),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/clone-samples/import" && init?.method === "POST") {
        expect(init.body).toBe(
          JSON.stringify({
            provider: "librivox",
            title: "Public Domain Reading - Chapter 1",
            speaker: "Ada Reader",
            audio_url: "https://archive.org/download/sample/chapter1.mp3",
            transcript: "Reviewed transcript for the sample.",
            transcript_source_url: "https://www.gutenberg.org/ebooks/123",
            source_url: "https://librivox.org/public-domain-reading/",
            license_label: "Public domain",
            provenance_note: "Review the transcript before importing.",
          }),
        );

        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 44,
            name: "Public Domain Reading - Chapter 1",
            engine: "qwen3_clone",
            transcript: "Reviewed transcript for the sample.",
          }),
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText("Search public voice samples"), {
      target: { value: "ada" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search samples" }));

    expect(await screen.findByText("Public Domain Reading - Chapter 1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Reviewed transcript"), {
      target: { value: "Reviewed transcript for the sample." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import reviewed sample" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/clone-samples/import", {
        body: JSON.stringify({
          provider: "librivox",
          title: "Public Domain Reading - Chapter 1",
          speaker: "Ada Reader",
          audio_url: "https://archive.org/download/sample/chapter1.mp3",
          transcript: "Reviewed transcript for the sample.",
          transcript_source_url: "https://www.gutenberg.org/ebooks/123",
          source_url: "https://librivox.org/public-domain-reading/",
          license_label: "Public domain",
          provenance_note: "Review the transcript before importing.",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });
  });

  it("creates a preset with multipart form data, shows progress, and refreshes the list", async () => {
    window.history.pushState({}, "", "/voices");

    const createdPreset = {
      id: 12,
      name: "Narration Voice",
      engine: "qwen",
      transcript: "Narration sample transcript for the saved preset.",
    };
    let listRequestCount = 0;

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload({
            default_export_voice_id: "preset:12",
          }),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && (!init || init.method === undefined)) {
        listRequestCount += 1;

        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (listRequestCount === 1 ? [] : [createdPreset]),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);

        const payload = init.body as FormData;
        expect(payload.get("name")).toBe("Narration Voice");
        expect(payload.get("transcript")).toBe("Narration sample transcript for the saved preset.");
        expect(payload.get("reference_audio")).toBeInstanceOf(File);
        expect((payload.get("reference_audio") as File).name).toBe("sample.wav");

        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => createdPreset,
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const displayNameInput = await screen.findByLabelText("Display name");

    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });

    fireEvent.change(displayNameInput, {
      target: { value: "Narration Voice" },
    });
    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Narration sample transcript for the saved preset." },
    });
    fireEvent.change(screen.getByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save cloned voice" }));

    expect(await screen.findByRole("button", { name: "Saving preset..." })).toBeDisabled();

    expect(await screen.findByText("1 cloned presets")).toBeInTheDocument();
    expect(screen.getByText("Narration Voice")).toBeInTheDocument();
  });

  it("transcribes a selected recording into an editable transcript before saving", async () => {
    window.history.pushState({}, "", "/voices");

    const createdPreset = {
      id: 21,
      name: "Recorded Voice",
      engine: "qwen3_clone",
      transcript: "Edited transcript from local transcription.",
    };
    let listRequestCount = 0;

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } satisfies FetchResponse);
      }
      if (typeof input === "string" && input === "/api/voices/presets" && (!init || init.method === undefined)) {
        listRequestCount += 1;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => (listRequestCount === 1 ? [] : [createdPreset]),
        } satisfies FetchResponse);
      }
      if (typeof input === "string" && input === "/api/voices/transcribe-reference" && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            transcript: "Draft transcript from local transcription.",
            language: "en",
            engine: "faster-whisper:base.en",
            segments: [],
          }),
        } satisfies FetchResponse);
      }
      if (typeof input === "string" && input === "/api/voices/presets" && init?.method === "POST") {
        const payload = init.body as FormData;
        expect(payload.get("transcript")).toBe("Edited transcript from local transcription.");
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => createdPreset,
        } satisfies FetchResponse);
      }

      return Promise.resolve({ ok: true, status: 200, json: async () => [] } satisfies FetchResponse);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const audioFile = new File(["audio"], "recording.wav", { type: "audio/wav" });

    const displayNameInput = await screen.findByLabelText("Display name");

    fireEvent.change(displayNameInput, {
      target: { value: "Recorded Voice" },
    });
    fireEvent.change(screen.getByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Transcribe audio" }));

    expect(await screen.findByDisplayValue("Draft transcript from local transcription.")).toBeInTheDocument();
    expect(screen.getByText("Transcript draft is ready to review.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Edited transcript from local transcription." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save cloned voice" }));

    expect(await screen.findByText("Recorded Voice")).toBeInTheDocument();
  });

  it("searches public clone samples and imports after transcript review", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } satisfies FetchResponse);
      }
      if (typeof input === "string" && input === "/api/voices/presets") {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } satisfies FetchResponse);
      }
      if (typeof input === "string" && input.startsWith("/api/clone-samples/search")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            query: "ada",
            items: [
              {
                id: "sample-1",
                provider: "librivox",
                title: "Public Reading - Chapter 1",
                speaker: "Ada Reader",
                audio_url: "https://archive.org/audio.mp3",
                transcript: null,
                transcript_source_url: "https://www.gutenberg.org/ebooks/123",
                source_url: "https://librivox.org/public-reading/",
                license_label: "Public domain or LibriVox-provided public-domain recording",
                provenance_note: "Candidate discovered through the LibriVox API.",
                is_importable: true,
              },
            ],
          }),
        } satisfies FetchResponse);
      }
      if (typeof input === "string" && input === "/api/clone-samples/import" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 44,
            name: "Public Reading - Chapter 1",
            engine: "qwen3_clone",
            transcript: "This is the reviewed transcript.",
            source_provider: "librivox",
            source_url: "https://librivox.org/public-reading/",
            transcript_source_url: "https://www.gutenberg.org/ebooks/123",
            license_label: "Public domain or LibriVox-provided public-domain recording",
            provenance_note: "Candidate discovered through the LibriVox API.",
          }),
        } satisfies FetchResponse);
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } satisfies FetchResponse);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(await screen.findByLabelText(/Search public voice samples/i), {
      target: { value: "ada" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Search samples/i }));

    expect(await screen.findByRole("button", { name: "Public Reading - Chapter 1" })).toBeInTheDocument();
    expect(screen.getByText(/Public domain or LibriVox/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Reviewed transcript/i), {
      target: { value: "This is the reviewed transcript." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Import reviewed sample/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/clone-samples/import",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("shows backend validation errors honestly when preset creation is rejected", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: async () => ({
            detail: "Transcript is required",
          }),
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const displayNameInput = await screen.findByLabelText("Display name");

    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });

    fireEvent.change(displayNameInput, {
      target: { value: "Narration Voice" },
    });
    fireEvent.change(screen.getByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save cloned voice" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Transcript is required");
    expect(screen.getByText("0 cloned presets")).toBeInTheDocument();
  });

  it("falls back to the response status when upload failures do not return json", async () => {
    window.history.pushState({}, "", "/voices");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: async () => {
            throw new SyntaxError("Unexpected token < in JSON");
          },
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const displayNameInput = await screen.findByLabelText("Display name");

    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });

    fireEvent.change(displayNameInput, {
      target: { value: "Narration Voice" },
    });
    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Narration sample transcript for the saved preset." },
    });
    fireEvent.change(screen.getByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save cloned voice" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed with status 500");
  });

  it("keeps the form honest when preset creation succeeds but the list refresh fails", async () => {
    window.history.pushState({}, "", "/voices");

    const createdPreset = {
      id: 12,
      name: "Narration Voice",
      engine: "qwen3_clone",
      transcript: "Narration sample transcript for the saved preset.",
    };
    let listRequestCount = 0;

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/settings") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/presets" && (!init || init.method === undefined)) {
        listRequestCount += 1;

        return Promise.resolve(
          listRequestCount === 1
            ? ({
                ok: true,
                status: 200,
                json: async () => [],
              } satisfies FetchResponse)
            : ({
                ok: false,
                status: 503,
                json: async () => ({
                  detail: "Voice preset library unavailable",
                }),
              } satisfies FetchResponse),
        );
      }

      if (typeof input === "string" && input === "/api/voices/presets" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => createdPreset,
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const displayNameInput = await screen.findByLabelText("Display name");

    const audioFile = new File(["audio"], "sample.wav", { type: "audio/wav" });

    fireEvent.change(displayNameInput, {
      target: { value: "Narration Voice" },
    });
    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Narration sample transcript for the saved preset." },
    });
    fireEvent.change(screen.getByLabelText("Reference audio file"), {
      target: { files: [audioFile] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save cloned voice" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Voice preset saved, but the preset list could not refresh. Voice preset library unavailable",
      );
    });
    expect(screen.getByLabelText("Display name")).toHaveValue("");
    expect(screen.getByLabelText("Transcript")).toHaveValue("");
    expect(screen.getByText("0 cloned presets")).toBeInTheDocument();
  });
});
