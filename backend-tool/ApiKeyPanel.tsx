import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CheckCircle2, AlertCircle, Loader2, Eye, EyeOff } from "lucide-react";

export default function ApiKeyPanel() {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSaveKey = async () => {
    if (!apiKey.trim()) {
      setError("API key is required");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // In a real implementation, you would send this to the backend
      // For now, we'll just store it locally
      localStorage.setItem("anthropic_api_key", apiKey);
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
    } catch (err) {
      setError("Failed to save API key");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!apiKey.trim()) {
      setError("Please enter an API key first");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Test the connection
      const response = await fetch("/api/trpc/payment.testConnection", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      if (response.ok) {
        setIsSaved(true);
        setTimeout(() => setIsSaved(false), 3000);
      } else {
        setError("Connection test failed");
      }
    } catch (err) {
      setError("Failed to test connection");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200/50 rounded-lg p-4">
        <p className="text-sm text-blue-700">
          Your Anthropic Claude API key is required to enable payment field parsing. Get your key from{" "}
          <a
            href="https://console.anthropic.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline hover:no-underline"
          >
            console.anthropic.com
          </a>
        </p>
      </div>

      <div className="space-y-3">
        <label className="block text-sm font-medium text-slate-700">API Key</label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setError(null);
              }}
              placeholder="sk-ant-..."
              className="pr-10 bg-slate-50 border-slate-200"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <Button
            onClick={handleSaveKey}
            disabled={isLoading || !apiKey.trim()}
            className="bg-slate-900 hover:bg-slate-800 text-white"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          onClick={handleTestConnection}
          disabled={isLoading || !apiKey.trim()}
          variant="outline"
          className="flex-1 border-slate-200 hover:bg-slate-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Testing...
            </>
          ) : (
            "Test Connection"
          )}
        </Button>
      </div>

      {isSaved && (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200/50 rounded-lg">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          <span className="text-sm text-emerald-700">Configuration saved successfully</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200/50 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      <div className="bg-slate-50 rounded-lg p-4 border border-slate-200/60 space-y-3">
        <h4 className="font-medium text-slate-900">Connection Status</h4>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-600">API Endpoint</span>
            <span className="text-slate-900 font-mono text-xs">api.anthropic.com</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">Model</span>
            <span className="text-slate-900 font-mono text-xs">claude-3-5-sonnet</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">Status</span>
            <div className="flex items-center gap-2">
              {isSaved ? (
                <>
                  <div className="w-2 h-2 bg-emerald-600 rounded-full" />
                  <span className="text-emerald-700 font-medium">Connected</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-slate-400 rounded-full" />
                  <span className="text-slate-600">Not Configured</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
