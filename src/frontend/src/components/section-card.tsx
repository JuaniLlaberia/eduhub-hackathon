import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Titled card that wraps every screen section. */
export function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

/** Skeleton placeholder: marks a section whose content is not built yet. */
export function Pending({ children }: { children?: React.ReactNode }) {
  return (
    <div className="text-muted-foreground rounded-md border border-dashed p-4 text-sm">
      {children ?? "En construcción"}
    </div>
  );
}
