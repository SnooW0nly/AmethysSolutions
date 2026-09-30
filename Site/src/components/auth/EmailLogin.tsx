"use client";

import { useState } from "react";
import { Mail, Lock, ArrowRight, CheckCircle, AlertCircle } from "lucide-react";

export default function EmailLogin() {
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/email/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccess(data.message);
        setStep("code");
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError("Erro ao enviar código. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/email/verify-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, code }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccess("Login realizado com sucesso!");
        // Redireciona para o dashboard
        setTimeout(() => {
          window.location.href = "/dashboard";
        }, 1000);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError("Erro ao verificar código. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setCode("");
    await handleSendCode(new Event("submit") as any);
  };

  return (
    <div className="w-full">
      {/* Email Step */}
      {step === "email" && (
        <form onSubmit={handleSendCode} className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-2 text-foreground/80">
              Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-foreground/40" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                className="w-full pl-10 pr-4 py-3 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-sm animate-in fade-in slide-in-from-top-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg hover:shadow-xl disabled:shadow-none"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Enviando...
              </>
            ) : (
              <>
                Enviar Código
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
      )}

      {/* Code Step */}
      {step === "code" && (
        <form onSubmit={handleVerifyCode} className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-2 text-foreground/80">
              Código de Verificação
            </label>
            <p className="text-sm text-foreground/60 mb-4">
              Enviamos um código de 6 dígitos para <strong className="text-primary">{email}</strong>
            </p>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-foreground/40" />
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                required
                maxLength={6}
                className="w-full pl-10 pr-4 py-4 bg-background/50 border border-foreground/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all text-center text-3xl font-mono tracking-[0.5em]"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-sm animate-in fade-in slide-in-from-top-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-500 text-sm animate-in fade-in slide-in-from-top-2">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || code.length !== 6}
            className="w-full py-3 bg-primary hover:bg-primary/90 disabled:bg-foreground/10 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg hover:shadow-xl disabled:shadow-none"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Verificando...
              </>
            ) : (
              <>
                Verificar Código
                <CheckCircle className="w-5 h-5" />
              </>
            )}
          </button>

          <div className="flex items-center justify-between text-sm pt-2">
            <button
              type="button"
              onClick={() => setStep("email")}
              className="text-foreground/60 hover:text-foreground transition-colors"
            >
              ← Voltar
            </button>
            <button
              type="button"
              onClick={handleResendCode}
              disabled={loading}
              className="text-primary hover:text-primary/80 transition-colors disabled:opacity-50 font-medium"
            >
              Reenviar código
            </button>
          </div>
        </form>
      )}

      {/* Info */}
      <div className="mt-6 p-4 bg-primary/10 border border-primary/20 rounded-xl">
        <p className="text-sm text-foreground/70">
          <span className="text-primary font-medium">Dica:</span> O código expira em 10 minutos. Você tem até 5 tentativas para inserir o código correto.
        </p>
      </div>
    </div>
  );
}
