import { useState } from "react";
import { Check, Code2, MonitorUp, Square } from "lucide-react";

interface ProfileViewerProps {
  cdpUrl: string | null;
  onStop: () => Promise<void>;
}

export function ProfileViewer({ cdpUrl, onStop }: ProfileViewerProps) {
  const [cdpCopied, setCdpCopied] = useState(false);
  const [stopping, setStopping] = useState(false);

  const copyCdpUrl = () => {
    if (!cdpUrl) return;
    const url = `${window.location.protocol}//${window.location.host}${cdpUrl}`;
    navigator.clipboard?.writeText(url).then(() => {
      setCdpCopied(true);
      setTimeout(() => setCdpCopied(false), 2000);
    }).catch((err) => console.warn("[cdp] copy failed:", err));
  };

  const stop = async () => {
    setStopping(true);
    try {
      await onStop();
    } finally {
      setStopping(false);
    }
  };

  return (
    <div className="h-full flex items-center justify-center bg-surface-0">
      <div className="w-full max-w-xl px-6 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border bg-surface-1 text-accent">
          <MonitorUp className="h-7 w-7" />
        </div>
        <h2 className="text-lg font-medium text-gray-100">Local browser window is open</h2>
        <p className="mt-2 text-sm text-gray-500">
          This profile is running in its own CloakBrowser instance.
        </p>

        <div className="mt-6 flex items-center justify-center gap-2">
          {cdpUrl && (
            <button
              type="button"
              onClick={copyCdpUrl}
              className={`btn-secondary flex items-center gap-2 ${cdpCopied ? "text-emerald-400" : ""}`}
            >
              {cdpCopied ? <Check className="h-4 w-4" /> : <Code2 className="h-4 w-4" />}
              {cdpCopied ? "Copied" : "Copy CDP URL"}
            </button>
          )}
          <button
            type="button"
            onClick={stop}
            disabled={stopping}
            className="btn-danger flex items-center gap-2"
          >
            <Square className="h-4 w-4" />
            {stopping ? "Stopping..." : "Stop"}
          </button>
        </div>
      </div>
    </div>
  );
}
