"use client";

import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Code
} from "@heroui/react";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {

  return (
    <Modal isOpen={true} isDismissable={false} hideCloseButton placement="center">
      <ModalContent>
        <ModalHeader>
          <div className="flex flex-col gap-1">
            <h2>Um erro ocorreu</h2>
            <span className="text-foreground/50 font-normal text-sm">
              Ocorreu um erro ao carregar a página. Por favor, tente novamente.
            </span>
          </div>
        </ModalHeader>
        <ModalBody>
          <Code color="default" className="text-foreground/50 font-normal p-4">
            {error.message}
          </Code>
        </ModalBody>
        <ModalFooter>
          <Button onPress={() => reset()} color="primary" className="w-full">Tentar novamente</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
