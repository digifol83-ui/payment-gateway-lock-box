import { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { CheckCircle2, AlertCircle, Loader2, ChevronDown } from "lucide-react";

export default function TransactionLog() {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { data, isLoading, error } = trpc.payment.getTransactions.useQuery({
    limit: 50,
    offset: 0,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-700">Failed to load transactions: {error.message}</p>
      </div>
    );
  }

  const transactions = data?.transactions || [];

  if (transactions.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">No transactions yet. Submit a payment to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {transactions.map((tx: any) => (
        <div key={tx.id} className="border border-slate-200/60 rounded-lg overflow-hidden">
          <button
            onClick={() => setExpandedId(expandedId === tx.id ? null : tx.id)}
            className="w-full p-4 hover:bg-slate-50 flex items-center justify-between transition-colors"
          >
            <div className="flex items-center gap-4 flex-1 text-left">
              <div className="flex items-center gap-3">
                {tx.validationStatus === "valid" ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                )}
              </div>
              <div className="flex-1">
                <p className="font-medium text-slate-900">{tx.maskedCardNumber}</p>
                <p className="text-sm text-slate-500">{tx.cardholderName}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-slate-900 capitalize">{tx.validationStatus}</p>
                <p className="text-xs text-slate-500">{new Date(tx.createdAt).toLocaleDateString()}</p>
              </div>
            </div>
            <ChevronDown
              className={`w-5 h-5 text-slate-400 transition-transform ${expandedId === tx.id ? "rotate-180" : ""}`}
            />
          </button>

          {expandedId === tx.id && (
            <div className="bg-slate-50 border-t border-slate-200/60 p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase mb-1">Card Number</p>
                  <p className="text-sm font-mono text-slate-900">{tx.maskedCardNumber}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase mb-1">Source</p>
                  <p className="text-sm text-slate-900 capitalize">{tx.source}</p>
                </div>
              </div>

              {tx.confidence && (
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase mb-2">Confidence Scores</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(tx.confidence).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex items-center justify-between bg-white p-2 rounded border border-slate-200/60">
                        <span className="text-xs text-slate-600 capitalize">{key}</span>
                        <span className="text-xs font-medium text-slate-900">{(value * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {tx.anomalies?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase mb-2">Anomalies</p>
                  <ul className="space-y-1 bg-amber-50 p-2 rounded border border-amber-200/50">
                    {tx.anomalies.map((anomaly: string, idx: number) => (
                      <li key={idx} className="text-xs text-amber-700">
                        • {anomaly}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
