"use client";

import type { ImgHTMLAttributes, ReactEventHandler, Ref } from "react";

import { useProtectedSrc } from "@/hooks/use-protected-src";
import { cn } from "@/lib/utils";

type ProtectedImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "src" | "alt"> & {
  resourceUrl: string;
  alt: string;
  imgRef?: Ref<HTMLImageElement>;
  onLoad?: ReactEventHandler<HTMLImageElement>;
};

export function ProtectedImage({ resourceUrl, alt, className, imgRef, onLoad, ...rest }: ProtectedImageProps) {
  const { src, error } = useProtectedSrc(resourceUrl);
  if (error && !src) {
    return <p className="px-3 py-6 text-center text-sm text-destructive">Image could not be loaded.</p>;
  }
  if (!src) {
    return <p className="px-3 py-6 text-center text-sm text-muted-foreground">Loading image…</p>;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={imgRef}
      src={src}
      alt={alt}
      data-testid="protected-image"
      className={cn("block h-auto w-full max-w-full", className)}
      onLoad={onLoad}
      {...rest}
    />
  );
}
