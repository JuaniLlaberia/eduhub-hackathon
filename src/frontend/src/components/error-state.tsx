import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// TODO: show errorMessage(error) from lib/api/errors once its tests are approved and it is implemented.
export function ErrorState({ error }: { error: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Algo salió mal</AlertTitle>
      <AlertDescription>{error instanceof Error ? error.message : String(error)}</AlertDescription>
    </Alert>
  );
}
