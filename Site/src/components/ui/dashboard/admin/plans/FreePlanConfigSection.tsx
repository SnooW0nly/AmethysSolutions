"use client";

import { useEffect, useState } from "react";
import {
  Button,
  Input,
  Switch,
  Select,
  SelectItem,
  Spinner,
  Chip,
} from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faRobot,
  faSave,
  faShield,
  faClock,
  faCalendarDays,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

type Plan = { id: string; name: string; zipFilename?: string };

type FreePlanConfig = {
  sourcePlanId: string;
  durationDays: number;
  active: boolean;
  minAccountAgeDays: number;
  maxRiskScore: number;
};

export function FreePlanConfigSection() {
  const [config, setConfig] = useState<FreePlanConfig>({
    sourcePlanId: "",
    durationDays: 7,
    active: true,
    minAccountAgeDays: 15,
    maxRiskScore: 60,
  });
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/admin/plans-config/free", { cache: "no-store" });
        const data = await res.json();
        if (data.config) setConfig(data.config);
        setPlans(data.plans || []);
      } catch {
        setError("Erro ao carregar configuração");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      if (!config.sourcePlanId) {
        setError("Selecione o plano de origem");
        return;
      }

      const res = await fetch("/api/admin/plans-config/free", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error || "Erro ao salvar");
      }
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.message || "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-10">
        <Spinner />
      </div>
    );
  }

  const plansWithZip = plans.filter((p) => p.zipFilename);
  const plansWithoutZip = plans.filter((p) => !p.zipFilename);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FontAwesomeIcon icon={faRobot} className="text-primary" />
          <div>
            <p className="font-semibold text-sm">Bot Free</p>
            <p className="text-xs text-foreground/60">
              Configure o plano gratuito oferecido aos usuários
            </p>
          </div>
        </div>
        <Switch
          isSelected={config.active}
          onValueChange={(v) => setConfig({ ...config, active: v })}
          size="sm"
        >
          <span className="text-xs">{config.active ? "Ativo" : "Inativo"}</span>
        </Switch>
      </div>

      {error && (
        <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-xs p-2">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg bg-success/10 border border-success/20 text-success-600 text-xs p-2">
          Configuração salva com sucesso!
        </div>
      )}

      {/* Plano de origem */}
      <div className="flex flex-col gap-1">
        <p className="text-xs text-foreground/70 font-medium">Plano de Origem (ZIP)</p>
        <p className="text-xs text-foreground/50 mb-1">
          O Bot Free usará o arquivo .zip deste plano
        </p>
        {plansWithoutZip.length > 0 && (
          <div className="rounded-md bg-warning/10 border border-warning/20 text-warning-600 text-xs p-2 mb-2 flex gap-2 items-center">
            <FontAwesomeIcon icon={faTriangleExclamation} />
            <span>
              {plansWithoutZip.length} plano(s) sem ZIP não aparecem na lista:{" "}
              {plansWithoutZip.map((p) => p.name).join(", ")}
            </span>
          </div>
        )}
        <div className="flex flex-col gap-1">
          {plansWithZip.map((p) => (
            <button
              key={p.id}
              onClick={() => setConfig({ ...config, sourcePlanId: p.id })}
              className={`text-left rounded-lg border p-3 transition-colors text-sm ${
                config.sourcePlanId === p.id
                  ? "border-primary bg-primary/10"
                  : "border-foreground/10 bg-foreground/2 hover:bg-foreground/5"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{p.name}</span>
                <Chip size="sm" color="success" variant="flat" className="text-[10px]">
                  ZIP ✓
                </Chip>
              </div>
              <span className="text-xs text-foreground/50">{p.id}</span>
            </button>
          ))}
          {plansWithZip.length === 0 && (
            <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-3 text-xs text-foreground/50">
              Nenhum plano com ZIP cadastrado. Faça upload de um ZIP em um plano primeiro.
            </div>
          )}
        </div>
      </div>

      {/* Duração */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <FontAwesomeIcon icon={faClock} className="text-foreground/50 text-xs" />
            <p className="text-xs text-foreground/70 font-medium">Duração (dias)</p>
          </div>
          <Input
            type="number"
            size="sm"
            value={String(config.durationDays)}
            onChange={(e) =>
              setConfig({ ...config, durationDays: Number(e.target.value) })
            }
            description="0 = sem expiração"
            min={0}
          />
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <FontAwesomeIcon icon={faCalendarDays} className="text-foreground/50 text-xs" />
            <p className="text-xs text-foreground/70 font-medium">Idade mínima da conta (dias)</p>
          </div>
          <Input
            type="number"
            size="sm"
            value={String(config.minAccountAgeDays)}
            onChange={(e) =>
              setConfig({ ...config, minAccountAgeDays: Number(e.target.value) })
            }
            description="Conta Discord mais nova é bloqueada"
            min={1}
          />
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <FontAwesomeIcon icon={faShield} className="text-foreground/50 text-xs" />
            <p className="text-xs text-foreground/70 font-medium">Score máximo de risco (0–100)</p>
          </div>
          <Input
            type="number"
            size="sm"
            value={String(config.maxRiskScore)}
            onChange={(e) =>
              setConfig({ ...config, maxRiskScore: Number(e.target.value) })
            }
            description="Acima disso, bloqueia o resgate"
            min={0}
            max={100}
          />
        </div>
      </div>

      {/* Score visual */}
      <div className="rounded-lg bg-foreground/5 border border-foreground/10 p-3 text-xs text-foreground/60">
        <p className="font-medium text-foreground/80 mb-1">Como funciona a detecção de risco:</p>
        <ul className="flex flex-col gap-0.5 list-disc list-inside">
          <li>+35 pts — Conta Discord com menos dias que o mínimo configurado</li>
          <li>+25 pts — IP identificado como VPN, proxy ou datacenter</li>
          <li>+20 pts — Múltiplas contas no mesmo IP nas últimas 72h</li>
          <li>+15 pts — Conta Discord nova (dentro do dobro do limite)</li>
          <li>+10 pts — E-mail descartável detectado</li>
          <li>+10 pts — Conta criada há menos de 30 minutos</li>
          <li>+5 pts — Sem e-mail vinculado</li>
        </ul>
        <p className="mt-2 text-foreground/50">
          Score atual de bloqueio: <span className="font-semibold text-danger">{config.maxRiskScore}</span> pts
        </p>
      </div>

      <Button
        color="primary"
        size="sm"
        className="self-start"
        onPress={handleSave}
        isLoading={saving}
        startContent={<FontAwesomeIcon icon={faSave} />}
      >
        Salvar configuração
      </Button>
    </div>
  );
}