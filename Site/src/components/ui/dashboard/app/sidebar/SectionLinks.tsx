"use client";

import { useMemo, useState } from "react";
import { useParams, usePathname, useRouter } from "next/navigation";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronDown } from "@fortawesome/free-solid-svg-icons";
import { AppSidebarGroup, getAppSidebarGroups } from "@/config/appSidebar";

type Group = AppSidebarGroup;

export function SectionLinks({ onNavigate }: { onNavigate?: () => void }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const appId = params?.id as string | undefined;

  const groups: Group[] = useMemo(() => {
    const base = `/dashboard/app/${appId}`;
    return getAppSidebarGroups(base);
  }, [appId]);

  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const g of groups) {
      initial[g.id] = true;
    }
    return initial;
  });

  const toggleGroup = (groupId: string) => {
    setExpanded((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  const betaSeparatorIndex = groups.findIndex((g) => g.disabled) === -1 ? Number.MAX_SAFE_INTEGER : groups.findIndex((g) => g.disabled);

  return (
    <nav className="">
      <div className="flex flex-col gap-2">
        {groups.map((g, idx) => {
          const isOpen = !!expanded[g.id];
          const isDisabledGroup = idx >= betaSeparatorIndex;
          return (
            <div key={g.id}>
              {idx === betaSeparatorIndex ? (
                <div className="flex items-center my-2" role="separator" aria-label="Em breve">
                  <div className="flex-1 h-px bg-foreground/10" />
                  <span className="mx-2 text-[10px] uppercase tracking-wider text-foreground/50">EM BREVE</span>
                  <div className="flex-1 h-px bg-foreground/10" />
                </div>
              ) : null}
              <button
                type="button"
                onClick={() => toggleGroup(g.id)}
                className="w-full px-2 py-1 text-left text-[11px] uppercase tracking-wide text-foreground/60 hover:text-foreground/80 flex items-center justify-between"
                aria-expanded={isOpen}
              >
                <span>{g.label}</span>
                <FontAwesomeIcon
                  icon={faChevronDown}
                  className={"transition-transform text-[11px] " + (isOpen ? "rotate-0" : "-rotate-90")}
                />
              </button>
              {isOpen ? (
                <ul className="flex flex-col gap-1">
                  {g.items.map((s) => {
                    if (g.disabled) {
                      return (
                        <li key={s.id}>
                          <div
                            className={
                              "w-full text-left rounded-md px-3 py-2 transition-colors flex items-center gap-2 cursor-not-allowed opacity-60 text-foreground/60"
                            }
                            aria-disabled="true"
                            title="Em breve"
                          >
                            <FontAwesomeIcon icon={s.icon} className="text-sm" />
                            <span className="text-sm">{s.label}</span>
                          </div>
                        </li>
                      );
                    }

                    const isActive = pathname?.startsWith(s.href);
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => {
                            router.push(s.href);
                            onNavigate?.();
                          }}
                          className={
                            "w-full text-left rounded-md cursor-pointer px-3 py-2 transition-colors flex items-center gap-2 " +
                            (isActive
                              ? "bg-foreground/5 text-foreground"
                              : "text-foreground/70 hover:text-foreground hover:bg-foreground/5")
                          }
                        >
                          <FontAwesomeIcon icon={s.icon} className="text-sm" />
                          <span className="text-sm">{s.label}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>
          );
        })}
      </div>
    </nav>
  );
}


