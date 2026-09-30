"use client";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { featuresPlans } from "@/config/features";

export function PricingFeatures() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
      {featuresPlans.map((feature, index) => (
        <div key={index} className="flex flex-col gap-1 max-w-sm md:max-w-2xs">
          <div className="flex gap-1 items-center">
            <FontAwesomeIcon icon={feature.icon} className="text-[12px]" />
            <span className="text-[0.875rem]">{feature.title}</span>
          </div>
          <p className="text-foreground/70 font-[370] text-[13px] leading-relaxed">{feature.description}</p>
        </div>
      ))}
    </div>
  );
}


