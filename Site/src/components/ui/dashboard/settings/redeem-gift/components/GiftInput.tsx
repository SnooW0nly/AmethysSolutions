import { Loader2 } from "lucide-react";
import { memo } from "react";

interface GiftInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  validating?: boolean;
}

function GiftInputComponent({ value, onChange, disabled = false, validating = false }: GiftInputProps) {
  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Digite o código do gift (ex: XXXX-XXXX-XXXX-XXXX)"
        disabled={disabled}
        className="w-full px-4 py-2.5 bg-foreground/10 border border-foreground/20 rounded-lg focus:outline-none focus:ring-2 focus:text-foreground focus:ring-primary focus:border-transparent transition-all placeholder:text-foreground/50 text-foreground/90 font-mono disabled:opacity-50"
      />
      {validating && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <Loader2 className="w-5 h-5 text-primary animate-spin" />
        </div>
      )}
    </div>
  );
}

export const GiftInput = memo(GiftInputComponent);


