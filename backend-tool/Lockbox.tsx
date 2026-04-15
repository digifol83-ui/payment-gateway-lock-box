import { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertCircle, CheckCircle2, Loader2, Lock } from "lucide-react";
import PaymentInputForm from "@/components/PaymentInputForm";
import TransactionLog from "@/components/TransactionLog";
import ApiKeyPanel from "@/components/ApiKeyPanel";

/**
 * Lockbox - Direct-access payment field parsing and validation dashboard
 * Opens immediately to the tool interface with no landing page
 */
export default function Lockbox() {
  const [activeTab, setActiveTab] = useState("parser");
  const [lastParsedTransaction, setLastParsedTransaction] = useState<any>(null);

  // Test connection mutation
  const testConnectionMutation = trpc.payment.testConnection.useMutation();

  const handleConnectionTest = async () => {
    await testConnectionMutation.mutateAsync();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200/60 bg-white/40 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg">
                <Lock className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Lockbox</h1>
                <p className="text-sm text-slate-500 mt-0.5">Payment Field Parsing & Validation</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {testConnectionMutation.isPending ? (
                <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg">
                  <Loader2 className="w-4 h-4 text-slate-600 animate-spin" />
                  <span className="text-sm text-slate-600">Testing...</span>
                </div>
              ) : testConnectionMutation.data?.success ? (
                <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 rounded-lg border border-emerald-200/50">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm text-emerald-700 font-medium">Connected</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 rounded-lg border border-amber-200/50">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span className="text-sm text-amber-700 font-medium">Not Tested</span>
                </div>
              )}
              <Button
                onClick={handleConnectionTest}
                disabled={testConnectionMutation.isPending}
                variant="outline"
                size="sm"
                className="border-slate-200 hover:bg-slate-50"
              >
                {testConnectionMutation.isPending ? "Testing..." : "Test Connection"}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-white border border-slate-200/60 p-1 rounded-lg shadow-sm">
            <TabsTrigger value="parser" className="rounded-md data-[state=active]:bg-slate-900 data-[state=active]:text-white">
              Payment Parser
            </TabsTrigger>
            <TabsTrigger value="log" className="rounded-md data-[state=active]:bg-slate-900 data-[state=active]:text-white">
              Transaction Log
            </TabsTrigger>
            <TabsTrigger value="settings" className="rounded-md data-[state=active]:bg-slate-900 data-[state=active]:text-white">
              API Configuration
            </TabsTrigger>
          </TabsList>

          {/* Payment Parser Tab */}
          <TabsContent value="parser" className="mt-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Input Form */}
              <div className="lg:col-span-2">
                <Card className="border-slate-200/60 bg-white shadow-sm">
                  <div className="p-8">
                    <div className="mb-6">
                      <h2 className="text-xl font-semibold text-slate-900 mb-2">Parse Payment Data</h2>
                      <p className="text-sm text-slate-500">Submit raw payment input for AI-powered field extraction</p>
                    </div>
                    <PaymentInputForm onSuccess={setLastParsedTransaction} />
                  </div>
                </Card>
              </div>

              {/* AI Analysis Panel */}
              <div>
                <Card className="border-slate-200/60 bg-white shadow-sm">
                  <div className="p-8">
                    <h3 className="text-lg font-semibold text-slate-900 mb-4">AI Analysis</h3>
                    {lastParsedTransaction ? (
                      <div className="space-y-4">
                        <div className="bg-slate-50 rounded-lg p-4 border border-slate-200/60">
                          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Confidence Scores</p>
                          <div className="space-y-2">
                            {lastParsedTransaction.parsed?.confidence &&
                              Object.entries(lastParsedTransaction.parsed.confidence).map(([key, value]: [string, any]) => (
                                <div key={key} className="flex items-center justify-between">
                                  <span className="text-sm text-slate-600 capitalize">{key}</span>
                                  <span className="text-sm font-medium text-slate-900">{(value * 100).toFixed(0)}%</span>
                                </div>
                              ))}
                          </div>
                        </div>

                        {lastParsedTransaction.parsed?.anomalies?.length > 0 && (
                          <div className="bg-amber-50 rounded-lg p-4 border border-amber-200/50">
                            <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-2">Anomalies Detected</p>
                            <ul className="space-y-1">
                              {lastParsedTransaction.parsed.anomalies.map((anomaly: string, idx: number) => (
                                <li key={idx} className="text-sm text-amber-700">
                                  • {anomaly}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {lastParsedTransaction.parsed?.rawAiReasoning && (
                          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200/60">
                            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">AI Reasoning</p>
                            <p className="text-sm text-slate-600 leading-relaxed">{lastParsedTransaction.parsed.rawAiReasoning}</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-sm text-slate-500">Submit a payment to see AI analysis</p>
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            </div>

            {/* Validation Results */}
            {lastParsedTransaction && (
              <div className="mt-8">
                <Card className="border-slate-200/60 bg-white shadow-sm">
                  <div className="p-8">
                    <h3 className="text-lg font-semibold text-slate-900 mb-6">Validation Results</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {[
                        { label: "Card Number", result: lastParsedTransaction.validation?.cardNumber },
                        { label: "Expiry Date", result: lastParsedTransaction.validation?.expiryDate },
                        { label: "CVV", result: lastParsedTransaction.validation?.cvv },
                        { label: "Cardholder Name", result: lastParsedTransaction.validation?.cardholderName },
                        { label: "Street Address", result: lastParsedTransaction.validation?.billingAddress?.street },
                        { label: "City", result: lastParsedTransaction.validation?.billingAddress?.city },
                      ].map((item, idx) => (
                        <div key={idx} className="p-4 rounded-lg border border-slate-200/60 bg-slate-50">
                          <p className="text-sm text-slate-600 mb-2">{item.label}</p>
                          <div className="flex items-center gap-2">
                            {item.result?.isValid ? (
                              <>
                                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                                <span className="text-sm font-medium text-emerald-700">Valid</span>
                              </>
                            ) : (
                              <>
                                <AlertCircle className="w-5 h-5 text-red-600" />
                                <span className="text-sm font-medium text-red-700">Invalid</span>
                              </>
                            )}
                          </div>
                          {item.result?.errors?.length > 0 && (
                            <p className="text-xs text-red-600 mt-2">{item.result.errors[0]}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* Transaction Log Tab */}
          <TabsContent value="log" className="mt-8">
            <Card className="border-slate-200/60 bg-white shadow-sm">
              <div className="p-8">
                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-slate-900 mb-2">Transaction History</h2>
                  <p className="text-sm text-slate-500">All parsed payments with validation status and masked card numbers</p>
                </div>
                <TransactionLog />
              </div>
            </Card>
          </TabsContent>

          {/* API Configuration Tab */}
          <TabsContent value="settings" className="mt-8">
            <Card className="border-slate-200/60 bg-white shadow-sm">
              <div className="p-8">
                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-slate-900 mb-2">API Configuration</h2>
                  <p className="text-sm text-slate-500">Manage your Anthropic Claude API key and connection settings</p>
                </div>
                <ApiKeyPanel />
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
