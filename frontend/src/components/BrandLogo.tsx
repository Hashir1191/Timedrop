import type { ImgHTMLAttributes } from "react";
type BrandLogoProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "src" | "alt"> & { variant?: "full" | "compact" };
export default function BrandLogo({ variant = "full", className = "", ...props }: BrandLogoProps) {
  return <img src={variant === "compact" ? "/brand/timedrop-mark.svg" : "/brand/timedrop-logo.svg"} alt="TimeDrop — Smart Parcel Delivery" className={className} {...props} />;
}
