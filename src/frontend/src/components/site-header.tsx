import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { isMockMode } from "@/lib/api/client";

// TODO: final product name and logo (open question in docs/teams/frontend.md).
export function SiteHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="font-semibold tracking-tight">
          EduHub
        </Link>
        {isMockMode && <Badge variant="secondary">Datos de ejemplo</Badge>}
      </div>
    </header>
  );
}
