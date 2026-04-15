import { useState } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Send } from "lucide-react";

interface PaymentInputFormProps {
  onSuccess?: (data: any) => void;
}

export default function PaymentInputForm({ onSuccess }: PaymentInputFormProps) {
  const [rawInput, setRawInput] = useState("");
  const parsePaymentMutation = trpc.payment.parsePayment.useMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawInput.trim()) return;

    const result = await parsePaymentMutation.mutateAsync({
      rawInput,
      source: "manual",
    });

    if (result.success && onSuccess) {
      onSuccess(result);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">Raw Payment Input</label>
        <Textarea
          value={rawInput}
          onChange={(e) => setRawInput(e.target.value)}
          placeholder="Paste raw payment data here. Example: Card 4532015112830366, expires 12/25, CVV 123, John Doe, 123 Main St, New York, NY 10001, USA"
          className="min-h-32 bg-slate-50 border-slate-200 focus:bg-white"
          disabled={parsePaymentMutation.isPending}
        />
      </div>

      <Button
        type="submit"
        disabled={parsePaymentMutation.isPending || !rawInput.trim()}
        className="w-full bg-slate-900 hover:bg-slate-800 text-white"
      >
        {parsePaymentMutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Parsing...
          </>
        ) : (
          <>
            <Send className="w-4 h-4 mr-2" />
            Parse Payment Data
          </>
        )}
      </Button>

      {parsePaymentMutation.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{parsePaymentMutation.error.message}</p>
        </div>
      )}
    </form>
  );
}
