"use client";

import { usePathname } from "next/navigation";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { ProductTopbar } from "@/components/layout/product-topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/" || pathname.startsWith("/auth/");
  if (isLanding) {
    return (
      <div className="flex min-h-screen flex-col">
        <ProductTopbar />
        <main className="flex-1">{children}</main>
      </div>
    );
  }
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <AppSidebar />
      <main className="flex-1 px-4 py-6 sm:px-8">{children}</main>
    </div>
  );
}
