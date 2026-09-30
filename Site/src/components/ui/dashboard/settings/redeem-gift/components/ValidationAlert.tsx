import { AlertCircle, CheckCircle } from "lucide-react";
import { GiftValidationResponse } from "../types";
import { formatDateSafe, buildDurationLabel } from "../utils";

export function ValidationAlert({ result }: { result: GiftValidationResponse }) {
  const isValid = result.valid;
  return (
    <div
      className={`p-3 rounded-lg flex items-start gap-2 ${
        isValid
          ? "bg-green-500/10 border border-green-500/20"
          : "bg-red-500/10 border border-red-500/20"
      }`}
    >
      {isValid ? (
        <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
      ) : (
        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
      )}
      <div className="flex-1">
        <p
          className={`text-sm font-medium ${
            isValid ? "text-green-500" : "text-red-500"
          }`}
        >
          {result.message}
        </p>
        {isValid && result.data && (
          <div className="mt-1 space-y-1 text-xs text-foreground/70">
            <p>
              <strong>Plano:</strong> {result.data.planName}
            </p>
            <p>
              <strong>Duração:</strong> {buildDurationLabel(result.data.months, result.data.days)}
            </p>
            {result.data.expiresAt && (
              <p>
                <strong>Expira em:</strong> {formatDateSafe(result.data.expiresAt)}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


