"use client";

import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Button, Link } from "@heroui/react";
import { usePathname } from "next/navigation";
import { names, User } from "@/config/dashboard";
import { useEffect, useState } from "react";

export const DashboardHeader = ({ user }: { user: User }) => {
    const activeTab = usePathname();
    const [hasExpiringApps, setHasExpiringApps] = useState(false);
    
    useEffect(() => {
        let mounted = true;
        const loadExpiringApps = async () => {
            try {
                const response = await fetch("/api/applications/expiring", {
                    credentials: "include",
                });
                if (!mounted) return;
                if (response.ok) {
                    const data = await response.json();
                    setHasExpiringApps(Boolean(data?.success && Array.isArray(data?.data) && data.data.length > 0));
                } else {
                    setHasExpiringApps(false);
                }
            } catch {
                if (!mounted) return;
                setHasExpiringApps(false);
            }
        };
        loadExpiringApps();
        return () => {
            mounted = false;
        };
    }, []);
    
    const tabs = [
        {
            label: "Aplicações",
            active: activeTab === "/dashboard",
            description: "Gerencie, visualize e configure seus serviços",
            href: "/dashboard",
        },
        {
            label: "Faturas",
            active: activeTab === "/dashboard/invoices",
            description: "Visualize e pague suas faturas",
            href: "/dashboard/invoices",
        },
        {
            label: "Configurações",
            active: activeTab === "/dashboard/settings",
            description: "Edite e configure suas informações da conta",
            href: "/dashboard/settings",
        },
        {
            label: "Painel de Administração",
            active: activeTab.startsWith("/dashboard/admin"),
            description: "Gerencie informações do sistema, como usuários, cupons, aplicações, etc.",
            href: "/dashboard/admin",
            hidden: !user?.admin,
        },
    ]
    return (
        <header className="items-center border-b border-foreground/10 mb-4">
            <div>
                <h1 className="text-2xl font-bold">{tabs.find((tab) => tab.active)?.label}</h1>
                <p className="text-foreground/70 text-sm">{tabs.find((tab) => tab.active)?.description}</p>
            </div>
            <div className="flex flex-row mt-2 justify-between w-full">
                <div className="flex flex-row gap-4">
                    {tabs.filter((tab) => !tab.hidden).map((tab) => (
                        <Link key={tab.label} href={tab.href} className={`py-2 text-sm ${tab.active ? "border-b-2 border-primary text-foreground" : "text-foreground/70 hover:text-foreground"}`}>
                            <span className="inline-flex items-center gap-1">
                                {tab.label}
                                {tab.href === "/dashboard/invoices" && hasExpiringApps && (
                                    <span
                                        aria-label="Há aplicações próximas do vencimento"
                                        title="Há aplicações próximas do vencimento"
                                        className="inline-block w-1.5 h-1.5 ml-0.5 rounded-full bg-red-500/80"
                                    />
                                )}
                            </span>
                        </Link>
                    ))}
                </div>
            </div>
        </header>
    )
}

export const DashboardMissing = () => {
    const activeTab = usePathname();
    return (
        <div className="flex flex-col w-full">
            <div className="bg-foreground/2 border border-foreground/10 text-foreground p-4 rounded-lg">
                <h1>{names.find((name) => name.tab === activeTab)?.title}</h1>
                <p className="text-foreground/70 text-sm">{names.find((name) => name.tab === activeTab)?.description}</p>
                <Button className="mt-2 w-fit bg-primary text-white rounded-lg" onPress={() => window.location.href = "/pricing"}>Comprar plano <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="text-[12px]" /></Button>
            </div>
        </div>
    )
}