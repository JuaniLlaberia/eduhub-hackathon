import { SiteHeader } from "@/components/site-header";

// Shared chrome of the product screens (analysis, dashboard, create, sandbox). The landing has its own.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
    </>
  );
}
