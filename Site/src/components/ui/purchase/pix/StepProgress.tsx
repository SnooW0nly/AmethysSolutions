"use client";

import React from "react";

type StepProgressProps = {
  steps: string[];
  current: number; // 1-based index
};

export default function StepProgress({ steps, current }: StepProgressProps) {
  return (
    <div className="w-full mb-4">
      <div className="flex items-center w-full gap-3">
        {steps.map((label, idx) => {
          const stepNumber = idx + 1;
          const isActive = stepNumber <= current;
          return (
            <React.Fragment key={label}>
              <div className="flex items-center gap-2">
                <div
                  className={
                    "h-9 w-9 rounded-full flex items-center justify-center font-semibold " +
                    (isActive
                      ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                      : "bg-foreground/10 text-foreground/60")
                  }
                >
                  {stepNumber}
                </div>
                <span
                  className={
                    "hidden sm:block text-sm " + (stepNumber === current ? "font-semibold" : "font-medium")
                  }
                >
                  {label}
                </span>
              </div>
              {idx < steps.length - 1 ? (
                <div
                  className={
                    "h-[2px] flex-1 " + (isActive ? "bg-primary/60" : "bg-foreground/15")
                  }
                />
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}


