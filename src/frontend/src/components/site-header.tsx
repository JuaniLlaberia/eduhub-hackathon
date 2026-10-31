import Link from "next/link";
import { NovaLogo } from "@/components/brand/nova-logo";
import { Badge } from "@/components/ui/badge";
import { isMockMode } from "@/lib/api/client";

export function SiteHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="rounded-sm">
          <NovaLogo className="text-lg" />
        </Link>
        {isMockMode && <Badge variant="secondary">Datos de ejemplo</Badge>}
      </div>
    </header>
  );
}
