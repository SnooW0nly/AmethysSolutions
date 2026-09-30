import { useState, useEffect, useRef } from "react";
import { Button, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, addToast, Chip, Avatar } from "@heroui/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faEdit, faImage, faPanorama } from "@fortawesome/free-solid-svg-icons";
import { CopyIconButton } from "../../CopyIconButton";
import { ChangeNameSection } from "./customization/ChangeNameSection";

interface BotCustomizationSectionProps {
  appId: string;
  botId: string;
  tokenConfigured: boolean;
  onUpdate: () => void;
}

export function BotCustomizationSection({ appId, botId, tokenConfigured, onUpdate }: BotCustomizationSectionProps) {
  return (
    <div className="flex flex-col">
        <div className="flex flex-col">
            <p className="font-semibold flex items-center gap-2">Personalização</p>
            <p className="text-xs text-foreground/60 max-w-[200px] xl:max-w-none">
                Defina as preferências visuais e comportamentais que deseja aplicar ao seu bot nesta aplicação.
            </p>
            <hr className="border-foreground/5 my-2" />
        </div>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mt-2">
            {/* Profile Setting */}
            <div className="flex flex-col gap-2 w-1/2">
              <ChangeNameSection />
            </div>
            {/* Preview Profile */}
            <div className="flex flex-col gap-2 w-1/2">
              <p>Preview Perfil</p>
            </div>
        </div>
    </div>
  );
}