"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// TODO (TDD: write handle-form.test.tsx first):
// - validate the handle (strip "@", lowercase, [a-z0-9_.]{1,30}, like the contract's Handle)
// - submit with useCreateAnalysis({ handle, max_posts: 200 }) and router.push(`/analisis/${job.id}`)
// - pending state on the button; show errorMessage(error) on failure
export function HandleForm() {
  return (
    <form className="flex w-full max-w-md gap-2" onSubmit={(event) => event.preventDefault()}>
      <Input name="handle" placeholder="@tucuenta" aria-label="Tu usuario de X" autoComplete="off" />
      <Button type="submit">Analizar</Button>
    </form>
  );
}
