"use client";

import { Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, Button, Switch, User as UserCell } from "@heroui/react";
import type { ApiUser } from "@/types/users";

export function ManageUserModal({
  isOpen,
  user,
  isAdminChecked,
  onAdminChange,
  onClose,
  onConfirm,
}: {
  isOpen: boolean;
  user: ApiUser | null;
  isAdminChecked: boolean;
  onAdminChange: (v: boolean) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal isOpen={isOpen} onOpenChange={() => onClose()}>
      <ModalContent>
        {() => (
          <>
            <ModalHeader>Gerenciar usuário</ModalHeader>
            <ModalBody>
              {user ? (
                <div className="flex flex-col gap-3 items-start justify-start w-full">
                  <UserCell avatarProps={{ radius: "lg", src: user.avatar || undefined }} name={user.globalName} description={`@${user.username} | ${user.email || "-"}`} />
                  <div className="flex flex-col gap-1 w-full">
                    <p className="text-xs text-foreground/70">Criado em: {user.createdAt ? new Date(user.createdAt).toLocaleDateString() : "-"}</p>
                    <p className="text-xs text-foreground/70">ID (DB): {user._id}</p>
                    <hr className="my-2 border-foreground/10" />
                    <Switch size="sm" isSelected={isAdminChecked} onValueChange={onAdminChange}>Administrador</Switch>
                  </div>
                </div>
              ) : null}
            </ModalBody>
            <ModalFooter>
              <Button variant="light" onPress={onClose}>Cancelar</Button>
              <Button color="primary" onPress={onConfirm}>Salvar</Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}


