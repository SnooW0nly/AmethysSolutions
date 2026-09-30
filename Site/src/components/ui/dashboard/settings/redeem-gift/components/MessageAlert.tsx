import { AlertCircle, CheckCircle } from "lucide-react";
import { GiftMessage } from "../types";

export function MessageAlert({ message }: { message: GiftMessage }) {
  const isSuccess = message.type === "success";
  return (
    <div
      className={`p-3 rounded-lg flex items-start gap-2 ${
        isSuccess
          ? "bg-green-500/10 border border-green-500/20"
          : "bg-red-500/10 border border-red-500/20"
      }`}
    >
      {isSuccess ? (
        <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
      ) : (
        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
      )}
      <p className={`text-sm ${isSuccess ? "text-green-500" : "text-red-500"}`}>
        {message.text}
      </p>
    </div>
  );
}


