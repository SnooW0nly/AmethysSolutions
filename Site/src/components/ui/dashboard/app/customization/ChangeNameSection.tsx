import { Input, Button } from "@heroui/react";
import { useState } from "react";


export function ChangeNameSection() {
  const [newUsername, setNewUsername] = useState("");
  return (
    <div>
      <div className="flex flex-col gap-2">
        <Input
            isClearable
            classNames={{
            label: "text-foreground/50",
            input: [
                "bg-transparent",
                "text-foreground/90",
                "placeholder:text-default-700/50 placeholder:text-white/60",
            ],
            innerWrapper: "bg-transparent",
            inputWrapper: [
                "rounded-lg",
                "bg-foreground/5",
                "border border-foreground/10",
                // "hover:bg-default-200/70",
                "group-data-[focus=true]:bg-foreground/5",
                "cursor-text",
            ],
            }}
            label="Nome de usuário"
            labelPlacement="outside"
            placeholder="Digite o novo nome de usuário"
            className="w-2/3"
            type="text"
        />
      </div>
    </div>
  );
}

function handleSaveNewUsername() {
  console.log("Salvar novo nome de usuário");
}