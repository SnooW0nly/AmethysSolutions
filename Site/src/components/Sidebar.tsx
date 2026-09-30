import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export function Sidebar({
    sections,
    selected,
    onSelect,
}: {
    sections: { id: string; label: string; href?: string; icon: any }[];
    selected: string;
    onSelect: (id: string) => void;
}) {
    return (
        <nav>
            <ul className="flex flex-col gap-1">
                {sections.map((s) => {
                    const isActive = s.id === selected;
                    return (
                        <li key={s.id}>
                            <button
                                type="button"
                                onClick={() => onSelect(s.id)}
                                className={
                                    `w-full text-left rounded-md cursor-pointer px-4 py-3 transition-colors flex items-center gap-2 ` +
                                    (isActive
                                        ? "bg-foreground/5"
                                        : "text-foreground/70 hover:text-foreground")
                                }
                            >
                                <FontAwesomeIcon icon={s.icon} />
                                <span className="text-sm">{s.label}</span>
                            </button>
                        </li>
                    );
                })}
            </ul>
        </nav>
    );
}