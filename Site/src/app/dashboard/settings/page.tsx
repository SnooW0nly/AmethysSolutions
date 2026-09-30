"use client";

import { DashboardHeader } from "@/components/ui/dashboard/DashboardHeader";
import { Loading } from "@/components/Loading";
import { Avatar, Button, Link } from "@heroui/react";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useRequireAuth } from "@/hooks/useAuth";
import RedeemGiftSection from "@/features/settings/components/RedeemGiftSection";
import AffiliateSection from "@/components/ui/dashboard/settings/AffiliateSection";

export default function Settings() {
    const { user, loading } = useRequireAuth();
  
    if (loading) return <Loading />;
    
    return (
        <main>
            {user && <DashboardHeader user={user} />}
            <section className="w-full flex flex-col gap-4">

                {/* Informações da conta */}
                <div className="flex flex-col gap-2 md:w-[50%]">
                    <div className="flex flex-col gap-1">
                        <span className="text-foreground/70 text-sm">Informações da conta</span>
                        <div className="flex flex-row gap-2 items-center bg-foreground/5 rounded-lg p-4 w-[100%]">
                            <Avatar src={user?.avatar || undefined} size="lg" />
                            <div className="flex flex-col min-w-0">
                                <span className="text-foreground text-sm font-semibold block truncate" title={`${user?.globalName} @${user?.username}`}>
                                    {user?.globalName} <span className="text-foreground/70 text-[12px] font-normal">@{user?.username}</span>
                                </span>
                                <span className="text-foreground/80 text-sm block truncate max-w-[200px] md:max-w-[300px]" title={user?.email || undefined}>{user?.email}</span>
                                <span className="text-foreground/70 text-[12px] font-[monoSpace]">{user?.id}</span>
                            </div>
                        </div>
                        <div className="flex flex-row gap-1">
                          <Link href={`https://discord.com/users/${user?.id}`} target="_blank">
                            <Button color="default" size="sm" variant="flat" className="flex flex-row items-center rounded-lg">
                              <span>Usuário no Discord <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="ml-1 text-[10px]" /></span>
                            </Button>
                          </Link>
                          <Link href="/logout">
                            <Button color="danger" size="sm" variant="flat" className="flex flex-row items-center rounded-lg">
                              <span>Encerrar sessão</span>
                            </Button>
                          </Link>
                        </div>
                    </div>
                </div>

                <hr className="border-foreground/10 md:w-[50%]" />

                {/* Resgatar Gift */}
                <RedeemGiftSection />

                <hr className="border-foreground/10 md:w-[50%]" />

                {/* Programa de Afiliados */}
                <div className="md:w-[50%]">
                    <AffiliateSection />
                </div>

            </section>
        </main>
    )
}