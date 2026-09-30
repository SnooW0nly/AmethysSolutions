"use client";

import { Chip, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow, User as UserCell, Button } from "@heroui/react";
import type { ApiUser } from "@/types/users";

export function UserTable({ users, loading, onManage }: { users: ApiUser[]; loading: boolean; onManage: (u: ApiUser) => void }) {
  return (
    <div className="w-full overflow-x-auto">
    <Table aria-label="Usuários" removeWrapper isStriped className="min-w-[720px]">
      <TableHeader>
        <TableColumn>NOME</TableColumn>
        <TableColumn>EMAIL/ID (DB)</TableColumn>
        <TableColumn>APLICAÇÕES/ID GLOBAL</TableColumn>
        <TableColumn>ADMIN</TableColumn>
        <TableColumn>AÇÕES</TableColumn>
      </TableHeader>
      <TableBody items={users} isLoading={loading} emptyContent={loading ? "Carregando..." : "Sem usuários"}>
        {(u: ApiUser) => (
          <TableRow key={u._id}>
            <TableCell>
              <UserCell avatarProps={{ radius: "lg", src: u.avatar || undefined }} name={u.globalName} description={`@${u.username}`} />
            </TableCell>
            <TableCell>{u.email || "-"}<br /><span className="text-xs text-foreground/30 font-[monoSpace]">{u._id}</span></TableCell>
            <TableCell>
              <span className="text-xs text-foreground/30 font-[monoSpace]">{Array.isArray(u.applications) ? u.applications.join(", ") : "-"}</span><br />
              <span className="text-xs text-foreground/30 font-[monoSpace]">{u._id}</span>
            </TableCell>
            <TableCell>
              <Chip size="sm" color={u.admin ? "primary" : "default"} variant="flat">{u.admin ? "sim" : "não"}</Chip>
            </TableCell>
            <TableCell>
              <div className="flex gap-2">
                <Button size="sm" variant="light" onPress={() => onManage(u)}>Gerenciar</Button>
              </div>
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
    </div>
  );
}


