"use client";

import { useState } from "react";
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Avatar, Skeleton, User, DropdownSection } from "@heroui/react";
import { Link } from "@heroui/link";
import { useAuth } from "@/hooks/useAuth";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChevronUp, faCube, faFileInvoice, faGear, faPlus, faRightFromBracket, faShield } from "@fortawesome/free-solid-svg-icons";


  
export const NavbarUserMenu = () => {
  const { user, loading } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  if (loading) {
    return (
      <Skeleton className="rounded-md">
        <div className="w-8 h-8 rounded-md bg-default-300" />
      </Skeleton>
    );
  }

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex gap-1 items-center justify-center py-1 px-3 hover:bg-primary/90 rounded-md transition-all duration-200 bg-primary md:w-fit"
      >
        <span className="text-foreground font-[500] font-sans text-[13px] flex items-center gap-1">
          Iniciar sessão
        </span>
      </Link>
    );
  }

  return (
    <Dropdown 
      placement="bottom-end" 
      onOpenChange={(open) => setIsOpen(open)} 
      classNames={{
        base: "before:bg-foreground/95",
        content:
          "py-1 px-1 border border-foreground/10 bg-background",
      }}
    >
      <DropdownTrigger>
        <div className="flex items-center gap-1 cursor-pointer">
          <Avatar
            as="button"
            className="transition-transform rounded-md h-8 w-8 cursor-pointer"
            src={user.avatar || undefined}
          />
          <FontAwesomeIcon
            icon={faChevronUp}
            className="text-sm transition-transform duration-200 text-[10px]"
            style={{ transform: isOpen ? "rotate(0deg)" : "rotate(-180deg)" }}
          />
        </div>
      </DropdownTrigger>
      <DropdownMenu
        className="p-2"
        disabledKeys={["profile"]}
        itemClasses={{
          base: [
            "rounded-lg",
            "transition-all duration-100",
            "data-[hover=true]:text-current",
            "data-[hover=true]:description:text-foreground/50",
            "outline-none",
            "select-none",
            "data-[focus-visible=true]:outline-none",
            "data-[hover=true]:bg-foreground/5",
            "data-[selectable=true]:focus:bg-foreground/5",
            "data-[pressed=true]:opacity-70",
            "data-[focus-visible=true]:ring-foreground/5",
          ],
        }}
      >
        <DropdownSection showDivider>
          <DropdownItem key="profile" isReadOnly className="h-14 gap-2 opacity-100">
            <User
              avatarProps={{
                size: "sm",
                src: user.avatar || undefined,
              }}
              classNames={{
                name: "text-foreground/90 font-semibold block max-w-[160px] truncate",
                description: "text-foreground/50 block max-w-[220px] truncate",
              }}
              description={`${user.email}`}
              name={`${user.globalName}`}
            />
          </DropdownItem>
        </DropdownSection>
        <DropdownSection showDivider>
          <DropdownItem
            key="new"
            description="Administrar aplicações"
            startContent={<FontAwesomeIcon icon={faCube} className="text-primary mr-2" />}
            onClick={() => {
              window.location.href = "/dashboard";
            }}
          >
            Painel de Controle
          </DropdownItem>
          <DropdownItem
            key="copy"
            description="Gerenciar faturas"
            startContent={<FontAwesomeIcon icon={faFileInvoice} className="text-primary mr-2" />}
            onClick={() => {
              window.location.href = "/dashboard/invoices";
            }}
          >
            Faturas
          </DropdownItem>
          <DropdownItem
            key="edit"
            description="Configurar a conta"
            startContent={<FontAwesomeIcon icon={faGear} className="text-primary mr-2" />}
            onClick={() => {
              window.location.href = "/dashboard/settings";
            }}
          >
            Preferências
          </DropdownItem>
          {user.admin ? (
            <DropdownItem
              key="admin"
              description="Administrar o sistema"
              startContent={<FontAwesomeIcon icon={faShield} className="text-primary mr-2" />}
              onClick={() => {
                window.location.href = "/dashboard/admin";
              }}
            >
              Painel de Administração
            </DropdownItem>
          ) : null}
        </DropdownSection>
        <DropdownSection>
          <DropdownItem
            key="delete"
            onClick={() => {
              window.location.href = "/logout";
            }}
            startContent={<FontAwesomeIcon icon={faRightFromBracket} className="text-danger mr-2" />}
          >
            Encerrar Sessão
          </DropdownItem>
        </DropdownSection>
      </DropdownMenu>
    </Dropdown>
  );
};
