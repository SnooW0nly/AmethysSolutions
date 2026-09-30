import { Spinner } from "@heroui/react";

export const Loading = () => {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <Spinner classNames={{label: "text-foreground mt-4"}} variant="default" />
    </div>
  );
}