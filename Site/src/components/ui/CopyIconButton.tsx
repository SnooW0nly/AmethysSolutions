"use client";

import { useEffect, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faCheck } from "@fortawesome/free-solid-svg-icons";

type CopyIconButtonProps = {
	value: string;
	className?: string;
	iconClassName?: string;
	ariaLabel?: string;
	title?: string;
	asSpan?: boolean;
	stopPropagation?: boolean;
	resetDelayMs?: number;
};

export function CopyIconButton({
	value,
	className,
	iconClassName = "text-[10px]",
	ariaLabel = "Copiar",
	title = "Copiar",
	asSpan = false,
	stopPropagation = false,
	resetDelayMs = 2000,
}: CopyIconButtonProps) {
	const [copied, setCopied] = useState(false);
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(() => {
		return () => {
			if (timerRef.current) clearTimeout(timerRef.current);
		};
	}, []);

	async function handleCopy(e?: React.SyntheticEvent) {
		if (stopPropagation && e) {
			if ("preventDefault" in e) e.preventDefault();
			if ("stopPropagation" in e) e.stopPropagation();
		}
		try {
			await navigator.clipboard.writeText(value || "");
			if (timerRef.current) clearTimeout(timerRef.current);
			setCopied(true);
			timerRef.current = setTimeout(() => setCopied(false), resetDelayMs);
		} catch {
			// ignore copy errors silently
		}
	}

	if (asSpan) {
		return (
			<span
				role="button"
				tabIndex={0}
				className={className}
				aria-label={ariaLabel}
				title={title}
				onClick={handleCopy}
				onKeyDown={(e) => {
					if (e.key === "Enter" || e.key === " ") handleCopy(e);
				}}
			>
				<FontAwesomeIcon icon={copied ? faCheck : faCopy} className={`${iconClassName} ${copied ? "text-green-500" : ""}`} />
			</span>
		);
	}

	return (
		<button
			type="button"
			className={className}
			aria-label={ariaLabel}
			title={title}
			onClick={handleCopy}
		>
			<FontAwesomeIcon icon={copied ? faCheck : faCopy} className={`${iconClassName} ${copied ? "text-green-500" : ""}`} />
		</button>
	);
}


