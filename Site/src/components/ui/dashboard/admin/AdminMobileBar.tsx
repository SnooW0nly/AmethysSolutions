"use client";

import { Button } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBars } from "@fortawesome/free-solid-svg-icons";

export function AdminMobileBar({ title, onOpen }: { title?: string; onOpen: () => void }) {
  return (
    <div className="flex md:hidden justify-between items-center">
      <h1 className="text-xl font-semibold">{title}</h1>
      <Button size="sm" variant="flat" onPress={onOpen}>
        <FontAwesomeIcon icon={faBars} className="mr-2" /> Menu
      </Button>
    </div>
  );
}


