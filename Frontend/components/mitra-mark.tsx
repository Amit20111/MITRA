import { useId } from "react";

/** Cyan folded-ribbon M, shared by navigation and the orbital core. */
export function MitraMark({
  size = 44,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const id = useId().replaceAll(":", "");
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 56"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient
          id={`${id}-cyan`}
          x1="8"
          y1="46"
          x2="48"
          y2="8"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#00e6ff" />
          <stop offset=".5" stopColor="#03b9f4" />
          <stop offset="1" stopColor="#7cecff" />
        </linearGradient>
        <linearGradient
          id={`${id}-fold`}
          x1="22"
          y1="10"
          x2="47"
          y2="45"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#54dcff" />
          <stop offset=".52" stopColor="#0083ca" />
          <stop offset="1" stopColor="#04e5ff" />
        </linearGradient>
      </defs>
      <path
        d="M8 44L20 13"
        stroke={`url(#${id}-cyan)`}
        strokeWidth="13"
        strokeLinecap="round"
      />
      <path
        d="M20 13L32 32L45 13"
        stroke={`url(#${id}-fold)`}
        strokeWidth="13"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M45 13L32 32"
        stroke={`url(#${id}-cyan)`}
        strokeWidth="13"
        strokeLinecap="round"
      />
      <path
        d="M49 27L56 44"
        stroke={`url(#${id}-fold)`}
        strokeWidth="13"
        strokeLinecap="round"
      />
    </svg>
  );
}
