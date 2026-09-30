"use client";

import { useEffect, useState } from "react";
import type { ApiUser } from "@/types/users";
import { UsersFilters } from "@/components/ui/dashboard/admin/users/Filters";
import { UserTable } from "@/components/ui/dashboard/admin/users/UserTable";
import { ManageUserModal } from "@/components/ui/dashboard/admin/users/ManageUserModal";
import { Button } from "@heroui/react";

export function UsuariosSection() {
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [adminFilter, setAdminFilter] = useState<string>("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [sort, setSort] = useState("createdAt_desc");

  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ApiUser | null>(null);
  const [configAdmin, setConfigAdmin] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const qs = new URLSearchParams({ page: String(page), limit: "10", ...(search ? { search } : {}), ...(adminFilter ? { admin: adminFilter } : {}), ...(from ? { from } : {}), ...(to ? { to } : {}), sort });
      const res = await fetch(`/api/admin/users?${qs.toString()}`, { cache: "no-store" });
      if (!res.ok) throw new Error("Erro ao carregar usuários");
      const data = await res.json();
      setUsers(Array.isArray(data?.users) ? data.users : []);
      setTotal(Number(data?.total || 0));
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, adminFilter, from, to, sort]);

  const saveAdmin = async (userId: string, admin: boolean) => {
    const res = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/admin`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ admin }) });
    if (res.ok) load();
  };

  const openConfig = (u: ApiUser) => { setSelectedUser(u); setConfigAdmin(!!u.admin); setIsConfigOpen(true); };
  const closeConfig = () => { setIsConfigOpen(false); setSelectedUser(null); };
  const confirmConfig = async () => { if (selectedUser) { await saveAdmin(selectedUser._id, configAdmin); closeConfig(); } };

  return (
    <div className="flex flex-col gap-3">
      {error ? <div className="rounded-lg bg-danger/10 border border-danger/20 text-danger-500 text-sm p-2">{error}</div> : null}
      <UsersFilters
        search={search}
        adminFilter={adminFilter}
        sort={sort}
        onChange={(next) => {
          if (next.search !== undefined) setSearch(next.search);
          if (next.adminFilter !== undefined) setAdminFilter(next.adminFilter);
          if (next.sort !== undefined) setSort(next.sort);
        }}
        onApply={() => { setPage(1); load(); }}
      />

      <UserTable users={users} loading={loading} onManage={openConfig} />
      <div className="flex items-center justify-between text-xs text-foreground/70">
        <span>Total: {total}</span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="light" isDisabled={page <= 1} onPress={() => setPage((p) => Math.max(1, p - 1))}>Anterior</Button>
          <span>Página {page}</span>
          <Button size="sm" variant="light" isDisabled={page * 10 >= total} onPress={() => setPage((p) => p + 1)}>Próxima</Button>
        </div>
      </div>

      <ManageUserModal
        isOpen={isConfigOpen}
        user={selectedUser}
        isAdminChecked={configAdmin}
        onAdminChange={setConfigAdmin}
        onClose={closeConfig}
        onConfirm={confirmConfig}
      />
    </div>
  );
}


