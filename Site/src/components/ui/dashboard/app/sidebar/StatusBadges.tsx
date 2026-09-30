import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrochip } from "@fortawesome/free-solid-svg-icons";

type StatusBadgesProps = {
  statusDisplay: { label: string; dotClass: string; animated?: boolean };
  utilizedRam?: number | null;
};

export function StatusBadges({ statusDisplay, utilizedRam }: StatusBadgesProps) {
  return (
    <div className="flex flex-row items-center justify-center gap-2 mt-2">
      <div className="w-1/2 py-1 px-3 rounded-full border border-foreground/5 text-[11px] text-foreground/70 flex items-center justify-center gap-1.5">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${statusDisplay.dotClass} ${statusDisplay.animated ? 'animate-pulse' : ''}`} />
        <span>{statusDisplay.label}</span>
      </div>
      <div className="w-1/2 py-1 px-3 rounded-full border border-foreground/5 text-[11px] text-foreground/70 flex items-center justify-center gap-1">
        <FontAwesomeIcon icon={faMicrochip} className="text-[10px] text-foreground/40" />
        <span>RAM: {utilizedRam ?? 0}MB</span>
      </div>
    </div>
  );
}


